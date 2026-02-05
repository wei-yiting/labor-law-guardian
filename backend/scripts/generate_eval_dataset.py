"""
RAG Evaluation Dataset Generation Script

This script automates the generation of RAG evaluation datasets using an "Ensemble & Rerank" architecture.

Architecture:
    1. Candidate Generation (Ensemble):
       - Uses multiple LLMs (Gemini, GPT, Claude) to generate diverse candidate questions
       - Each model brings different strengths to question formulation and logic design
    2. Judging & Selection (Rerank):
       - A designated Judge Model evaluates all candidates
       - Filters out low-quality or single-hop (Level 1) questions
       - Selects the best examples to form the final dataset

Configuration:
    - GENERATION_MODEL_*: defined in script constants (GEMINI, GPT, CLAUDE)
    - JUDGE_MODEL: defined in script constants
    - Input: JSON file containing law chunks or context data
    - Output: Standardized Evaluation Dataset JSON

Usage:
    uv run python backend/scripts/generate_eval_dataset.py ./path/to/data.json
    uv run python backend/scripts/generate_eval_dataset.py ./path/to/directory/ --dry-run
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import questionary


# LangChain Imports
from langchain.chat_models import init_chat_model
from langchain_core.runnables import (
    RunnableParallel,
    RunnableLambda,
    RunnablePassthrough,
)
from pydantic import BaseModel

# Project Imports
# Adjust python path to ensure backend modules can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from backend.app.rag.types import (
    EvalQuestionCandidate,
    EvalDatasetItem,
)
from backend.app.prompt_manager import PromptTemplateRegistry

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
)
logger = logging.getLogger("rag_gen_eval")

# --- Semantic Constants ---

GENERATION_MODEL_GEMINI = "gemini-2.5-pro"
GENERATION_MODEL_GPT = "gpt-5.2"
GENERATION_MODEL_CLAUDE = "claude-sonnet-4-5"

JUDGE_MODEL = "gemini-2.5-pro"

DEFAULT_GENERATION_COUNT = 15
DEFAULT_FINAL_COUNT = 15

# Prompts are now managed via PromptTemplateRegistry
# See backend/prompts/manifest.json and backend/prompts/retrieval_eval_gen/*.prompty

# --- Helper Classes ---


class CandidatesListOutput(BaseModel):
    """Wrapper for list of candidates."""

    candidates: List[EvalQuestionCandidate]


class EvalDatasetOutput(BaseModel):
    """Temporary wrapper for structure output of final dataset items."""

    items: List[EvalDatasetItem]


# --- Helper Functions ---


def recursive_find_json_files(paths: List[str]) -> List[Path]:
    """Recursively find all JSON files in the given paths."""
    found_files = []
    for p in paths:
        path_obj = Path(p)
        if path_obj.is_file():
            if path_obj.suffix.lower() == ".json":
                found_files.append(path_obj)
        elif path_obj.is_dir():
            found_files.extend(path_obj.rglob("*.json"))
    return sorted(list(set(found_files)))


def load_json_content(file_path: Path) -> Any:
    """Load JSON content from file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None


def load_env_from_root():
    """
    Load .env file from the project root (assumed to be ../.env relative to this script).
    This is a fallback since uv run --env-file is failing with permission errors.
    """
    # script is in backend/scripts/generate_eval_dataset.py
    # root is backend/../ -> ../
    # But we resolve relative to the script location
    script_dir = Path(__file__).resolve().parent
    # backend/scripts/../../.env -> project_root/.env
    env_path = script_dir.parent.parent / ".env"

    try:
        if env_path.exists():
            logger.info(f"Loading environment variables from {env_path}")
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, value = line.split("=", 1)
                            # Remove quotes if present
                            key = key.strip()
                            value = value.strip().strip("'").strip('"')
                            if key and value:
                                os.environ[key] = value
            except Exception as e:
                logger.warning(f"Failed to read .env file: {e}")
        else:
            logger.warning(f".env file not found at {env_path}")
    except (PermissionError, OSError) as e:
        logger.warning(f"Permission denied accessing .env file at {env_path}: {e}")
        logger.warning("Please ensure environment variables are set manually.")


# --- Main Logic ---


class DatasetGenerator:
    def __init__(
        self,
        target_level: str,
        generation_count: int,
        final_count: int,
        user_instructions: str = "",
        dry_run: bool = False,
    ):
        self.target_level = target_level
        self.generation_count = generation_count
        self.final_count = final_count
        self.user_instructions = user_instructions
        self.dry_run = dry_run

        # Initialize Prompt Registry
        self.prompt_registry = PromptTemplateRegistry()

        # Select prompt task names based on target level
        if "Level 3" in self.target_level:
            self.gen_prompt_name = "retrieval_eval_dataset_l3_candidate_gen"
            self.judge_prompt_name = "retrieval_eval_dataset_l3_judge_rerank"
        else:
            self.gen_prompt_name = "retrieval_eval_dataset_l1_candidate_gen"
            self.judge_prompt_name = "retrieval_eval_dataset_l3_judge_rerank"  # Fallback or future L1 judge

        if not self.dry_run:
            try:
                self.gen_models = {
                    "gemini": init_chat_model(
                        GENERATION_MODEL_GEMINI, model_provider="google_genai"
                    ),
                    "gpt": init_chat_model(
                        GENERATION_MODEL_GPT, model_provider="openai"
                    ),
                    "claude": init_chat_model(
                        GENERATION_MODEL_CLAUDE, model_provider="anthropic"
                    ),
                }
                self.judge_model = init_chat_model(
                    JUDGE_MODEL, model_provider="google_genai"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize models: {e}")
                logger.warning("Generation will fail unless in dry-run mode.")
                self.gen_models = {}
                self.judge_model = None
        else:
            logger.info("Dry run: Skipping model initialization.")
            self.gen_models = {}
            self.judge_model = None

    def _get_generation_chain(self, model_name: str, model):
        """Creates a generation chain for a single model using prompt registry."""
        # Load prompt template from registry
        prompt = self.prompt_registry.get_prompt_template(self.gen_prompt_name)

        # Ensure structured output
        if self.dry_run:
            # Return a dummy chain for dry run structure
            return RunnableLambda(lambda x: CandidatesListOutput(candidates=[]))

        try:
            # We want a list of candidates directly.
            # ChatStatement -> CandidatesListOutput
            structured_llm = model.with_structured_output(CandidatesListOutput)
        except Exception:
            # Fallback for models without native structured output support (if any)
            structured_llm = model

        chain = prompt | structured_llm
        return chain

    def _process_candidates(self, inputs: Dict[str, Any]) -> str:
        """
        Aggregates candidate questions from parallel LLM calls.
        Input is a Dict where keys are model names and values are List[EvalQuestionCandidate] or dicts.
        """
        all_candidates = []
        for model_name, result in inputs.items():
            if isinstance(result, CandidatesListOutput):
                # Covers both CandidatesListOutput (which is list[T]) and raw lists
                for item in result.candidates:
                    # Handle both Pydantic model and dict (from dry run or fallback)
                    candidate = (
                        item.model_dump() if hasattr(item, "model_dump") else item
                    )
                    if isinstance(candidate, dict):
                        candidate["source_model"] = model_name
                        all_candidates.append(candidate)
            else:
                logger.warning(
                    f"Unexpected result format from {model_name}: {type(result)} (expected CandidatesListOutput)"
                )

        return json.dumps(all_candidates, ensure_ascii=False, indent=2)

    async def run_pipeline(self, context_law_chunks: str) -> List[EvalDatasetItem]:
        """
        Executes the full chain:
        1. Parallel Generation (Gemini, GPT, Claude)
        2. Aggregation
        3. Judging & Selection
        """
        if self.dry_run:
            logger.info("Dry run: Returning empty dataset.")
            return []

        # 1. Prepare Parallel Chains
        parallel_branches = {}
        for name, model in self.gen_models.items():
            parallel_branches[name] = self._get_generation_chain(name, model)

        parallel_chain = RunnableParallel(**parallel_branches)

        # 2. Prepare Judge Chain
        # Load judge prompt template from registry
        judge_prompt = self.prompt_registry.get_prompt_template(self.judge_prompt_name)
        judge_chain = judge_prompt | self.judge_model.with_structured_output(
            EvalDatasetOutput
        )

        # 3. Construct Full Pipeline (LCEL)
        # Input: {"questions_count": ..., "context_law_chunks": ...}
        # Step 1: Generate Candidates -> {"gemini": ..., "gpt": ...}
        # Step 2: Process -> "candidates_json_string"
        # Step 3: Judge -> EvalDatasetOutput

        # We need to pass context_law_chunks to Judge as well.
        # So we use passthrough or assign it.

        full_chain = (
            RunnablePassthrough.assign(candidates_raw=parallel_chain)
            | RunnablePassthrough.assign(
                candidate_questions=RunnableLambda(
                    lambda x: self._process_candidates(x["candidates_raw"])
                )
            )
            | judge_chain
        )

        input_vars = {
            "questions_count": self.generation_count,  # Mapped to prompt variable
            "context_law_chunks": context_law_chunks,
            "final_question_count": self.final_count,
            "user_instructions": self.user_instructions,
        }

        logger.info("Starting pipeline execution...")
        result = await full_chain.ainvoke(input_vars)

        if isinstance(result, EvalDatasetOutput):
            return result.items
        return []


async def main_async():
    parser = argparse.ArgumentParser(description="Generate RAG Eval Dataset")
    parser.add_argument("inputs", nargs="+", help="Input files or directories")
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (no LLM calls)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Specific output filename (only valid for single input file)",
    )
    args = parser.parse_args()

    # Load Env
    load_env_from_root()

    # 1. Recursive Scan
    logger.info("Scanning input files...")
    files = recursive_find_json_files(args.inputs)
    logger.info(f"Found {len(files)} JSON files.")

    if not files:
        logger.error("No JSON files found. Exiting.")
        sys.exit(1)

    if args.output and len(files) > 1:
        logger.error(
            "Error: --output argument can only be used with a single input file."
        )
        sys.exit(1)

    # 2. Interactive Wizard
    if not args.dry_run:
        answers = await questionary.form(
            target_level=questionary.select(
                "Select Target Level:",
                choices=["Level 3 (Multi-Hop/Reasoning)", "Level 1 (Single-Hop)"],
            ),
            generation_count=questionary.text(
                "Generation Count per Model:",
                default=str(DEFAULT_GENERATION_COUNT),
                validate=lambda x: x.isdigit(),
            ),
            final_count=questionary.text(
                "Final Count per Context:",
                default=str(DEFAULT_FINAL_COUNT),
                validate=lambda x: x.isdigit(),
            ),
            output_suffix=questionary.text(
                "Output Filename Suffix (e.g. 'run1' -> eval_filename_run1.json):",
                default="",
            ),
            user_instructions=questionary.text(
                "Additional User Instructions (Optional):",
                default="",
                multiline=True,
            ),
        ).ask_async()

        if not answers:
            logger.info("Cancelled.")
            sys.exit(0)

        target_level = answers["target_level"]
        generation_count = int(answers["generation_count"])
        final_count = int(answers["final_count"])
        output_suffix = answers.get("output_suffix", "").strip()
        user_instructions = answers.get("user_instructions", "").strip()
        if not user_instructions:
            user_instructions = "無 (None)"
    else:
        target_level = "Level 3"
        generation_count = 1
        final_count = 1
        output_suffix = ""
        user_instructions = "Dry Run Instructions"
        logger.info("Dry run: Using default Mock settings.")

    generator = DatasetGenerator(
        target_level, generation_count, final_count, user_instructions, args.dry_run
    )

    # Resolve output directory relative to PROJECT ROOT, not CWD
    # This script is in backend/scripts/generate_eval_dataset.py
    # We want backend/data/eval_dataset/subset
    project_root = Path(__file__).resolve().parent.parent.parent  # labor-law-guardian/
    output_dir = project_root / "backend/data/eval_dataset/subset"
    output_dir.mkdir(parents=True, exist_ok=True)

    total_generated = 0

    for file_path in files:
        logger.info(f"Processing {file_path.name}...")
        data = load_json_content(file_path)
        if not data:
            continue

        context_str = json.dumps(data, ensure_ascii=False, indent=2)

        # Execute Pipeline
        final_items = await generator.run_pipeline(context_str)

        # Save Output
        if final_items:
            if args.output:
                output_filename = output_dir / args.output
                # Ensure it has .json extension
                if not output_filename.suffix == ".json":
                    output_filename = output_filename.with_suffix(".json")
            else:
                # Use suffix from interactive mode if available
                base_name = f"eval_{file_path.stem}"
                if output_suffix:
                    base_name += f"_{output_suffix}"
                output_filename = output_dir / f"{base_name}.json"

            # Convert to list of dicts for saving
            output_data = [item.model_dump() for item in final_items]

            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(final_items)} items to {output_filename}")
            total_generated += len(final_items)

            # Summary
            logger.info("====================================")
            logger.info(f"Results for {file_path.name}")
            logger.info("====================================")
            logger.info(f"Metric: Generated Items")
            logger.info(f"Value: {len(final_items)}")
            logger.info("====================================")
        else:
            logger.warning("No dataset items produced.")

    logger.info(f"Total evaluation items generated: {total_generated}")


if __name__ == "__main__":
    asyncio.run(main_async())
