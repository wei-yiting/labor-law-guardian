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
from langchain_core.prompts import ChatPromptTemplate
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

LEVEL_3_GENERATION_SYSTEM_PROMPT = """
你是一位精通台灣勞動法令的資料工程專家 (Legal Data Engineer)。
你的任務是基於『』內提供的法律文本，生成 {questions_count} 組高品質的 **Level 3 (Multi-Hop) RAG 評測問答集**。

### 特別指令 (User Instructions)
請特別注意 User Prompt 中來自使用者的額外指引，並將其邏輯應用於題目生成。

### 核心目標：Level 3 (Multi-Hop Retrieval) 評測
評測重點在於驗證檢索系統是否具備「跨區塊 (Cross-Chunk) 關聯」的能力。
你生成的每一個題目，必須 **嚴格要求** 檢索系統同時查找並結合 **至少三個不同的 Chunk (Text Segment)** 才能獲得完整答案。

### 題目設計規範 (Strict Design Rules)
1.  **隱含式提問 (Implicit Reference)**：
    * **嚴禁** 在題目中出現「依據第幾條...」、「參照勞基法第 XX 條...」或「第 X 項第 Y 款」等明確指引。
    * 題目必須模擬真實使用者的自然語言情境（例如：「雇主若發生...情況，會有什麼後果？」），迫使檢索系統依賴語意理解而非關鍵字匹配。

2.  **實體法條依據 (Fact-Based)**：
    * 答案必須 **完全基於** 提供的 `input_context` 內容。不可使用外部知識或自行推測。
    * 若 Input 中缺乏回答該問題所需的某個 Chunk，請勿生成該題。

3.  **Reference ID 聚合規則**：
    * 雖然輸入是 Chunks，但輸出的 `reference_articles_id` 請填寫該 Chunk 對應的 `parent_id`（即法條編號，如 "LSA-32"）。
    * 若一題用到了 `LSA-32_P1` 和 `LSA-79_P1`，Reference 應輸出 `[["LSA-32", "LSA-79"]]`。

### 強制跨 Chunk 邏輯類型 (Required Logic Types)
你必須混合使用以下邏輯來建構題目：

* **Type A - 違法與罰則 (Violation & Penalty)**：
    * *邏輯*：結合「禁止/義務規定 Chunk」與「罰則 Chunk」。
    * *範例*：雇主違反「延長工時需經工會同意(LSA-32)」的規定，會被「處以多少罰鍰(LSA-79)」？
* **Type B - 母法與細則/規則 (Cross-Document)**：
    * *邏輯*：結合「母法 Chunk」的原則與「細則/請假規則 Chunk」的細節。
    * *範例*：勞基法規定有「婚假(LSA-43)」，請假規則規定了「具體天數與給薪(LEAVE_RULE-2)」。
* **Type C - 定義與排除 (Definition & Exception)**：
    * *邏輯*：結合「定義 Chunk」與「排除條款 Chunk」。
    * *範例*：工資定義在 LSA-2，但細則 ENF_RULE-10 規定了哪些「不屬於經常性給與」。
* **Type D - 跨項次條文 (Intra-Article, Cross-Chunk)**：
    * *邏輯*：同一個法條的不同項次被切分成不同 Chunks，需結合回答。
    * *範例*：LSA-9-1_P1 規定競業禁止需有合理補償，LSA-9-1_P2 規定該補償「不包括」工作期間的給付。題目需結合兩者（如：「約定競業禁止時，可否將在職薪資視為合理補償？」）。

### 輸出格式 (JSON Format)
請直接輸出一個 JSON Array，格式如下：

```json
[
  {{
    "question": "具體的情境問題（不含法條編號）",
    "ground_truth": "結合多個 Chunks 內容的完整答案",
    "reference_articles_id": [["LSA-XX", "ENF_RULE-YY"]] // 必須包含所有用到的來源 parent_id，包在 List 中
  }}
]
```

### 優良範例 (Few-Shot Examples)

**範例 1 (Type A - 違法與罰則 | Violation & Penalty):**
* **Question**: 若雇主因天災、事變等突發事件，認為有繼續工作之必要而停止勞工的假期，但在事後卻沒有依規定在二十四小時內詳述理由報請主管機關核備，依法最高可處以多少罰鍰？
* **Ground Truth**: 雇主若停止勞工假期，應於事後二十四小時內詳述理由報請當地主管機關核備；若違反此規定，處新臺幣二萬元以上一百萬元以下罰鍰。
* **Logic**: 需結合 `LSA-40` (規定停止假期需於24小時內核備) 與 `LSA-79` (針對違反第40條之罰則)。單看 LSA-40 無法得知罰鍰金額。
* **Reference IDs**: [["LSA-40", "LSA-79"]]

**範例 2 (Type B - 母法與細則/規則跨搜 | Cross-Document):**
* **Question**: 勞工因結婚依法律規定可請幾天婚假？這段期間雇主是否應照給工資？
* **Ground Truth**: 勞工結婚者給予婚假八日，工資照給。
* **Logic**: 母法 `LSA-43` 僅提到勞工因婚喪得請假，但具體天數與給薪規範在《勞工請假規則》的 `LEAVE_RULE-2`。系統必須跨文檔檢索才能回答具體天數。
* **Reference IDs**: [["LSA-43", "LEAVE_RULE-2"]]

**範例 3 (Type D - 同法條跨項次/Chunk | Intra-Article, Cross-Chunk):**
* **Question**: 雇主與勞工約定「離職後競業禁止」條款時，若聲稱「勞工在職期間領取的薪資已經包含未來的補償費了」，這樣的約定是否符合法律對「合理補償」的定義？
* **Ground Truth**: 不符合。法律明文規定，離職後競業禁止之合理補償，不包括勞工於工作期間所受領之給付。
* **Logic**: 需結合 `LSA-9-1` 的不同項次。第一項(Chunk P1)規定需有合理補償，第二項(Chunk P2)明確排除在職期間薪資。需同時參照兩者才能判定該主張無效。
* **Reference IDs**: [["LSA-9-1"]]

**範例 4 (Type C - 定義與排除 | Definition & Exception):**
* **Question**: 雇主在計算勞工的「平均工資」時，若勞工曾因職業災害而在醫療中不能工作，這段期間是否應計入平均工資的計算天數中？
* **Ground Truth**: 不計入。依規定計算平均工資時，因職業災害尚在醫療中之期間均不計入。
* **Logic**: 母法 `LSA-2` 定義了平均工資的計算公式（前六個月工資總額/總日數），但施行細則 `ENF_RULE-2` 規定了職災醫療期間應予以排除不計。
* **Reference IDs**: [["LSA-2", "ENF_RULE-2"]]

---

### 開始生成
請基於以下『』中提供的法律文本片段 (`input_context`)，嚴格遵守上述規則與邏輯，生成 {questions_count} 個 Level 3 題目：

『
{context_law_chunks}
』
"""


LEVEL_3_JUDGE_SYSTEM_PROMPT = """
你是一位嚴格的 **RAG 評測資料集審計員 (Lead Legal Dataset Auditor)**。
你的工作是審核由多個 LLM 生成的「候選問題集」，並從中篩選並優化出最優質、符合 **Level 3 (Multi-Hop)** 標準的題目。

### 任務目標
從「「」」裡的候選問題集 (Candidate Questions) 之中，依據『』裡的法律文本原始資料 (Source Text)進行嚴格審核與增強，最終輸出 **{final_question_count}** 個高品質題目。
輸出必須嚴格符合指定的 JSON Schema。

### 特別指令 (User Instructions)
審核時請確認題目是否符合 User Prompt 中的額外指引，若有違反請視為不合格或進行修正。

### 執行流程 (Chain of Thought Process)
請對每一個候選題目，**Step-by-Step** 執行以下三個階段的思考與處理：

#### 階段一：資格初篩 (Pass/Fail Gate)
若題目符合以下任一「失敗條件」，請直接 **剔除 (Discard)**：
1.  **假性 Level 3 (Fake Multi-Hop)**：如果問題僅透過 **單一** Chunk 或 **單一** 法條即可獲得完整答案，視為 Level 1，直接剔除。
2.  **顯性引用 (Explicit Reference)**：題目中若出現「依照第 XX 條...」等具體指引，直接剔除。
3.  **範圍外 (Out of Scope)**：問題無法僅從提供的 `Source Text` 回答，或涉及外部知識。

#### 階段二：驗證與增強 (Validation & Enrichment)
針對通過初篩的題目，進行深度驗證並生成 Metadata：
1.  **正確性驗證 (Correctness Check)**：
    *   嚴格比對 `ground_truth` 與 `Source Text`。若答案有誤或不精確，請依據原文修正；若無法修正則剔除。
2.  **引用校對 (Ref ID Validation)**：
    *   檢查 `reference_articles_id` 是否正確列出了所有必要的 Parent ID (如 "LSA-32")。
    *   修正任何遺漏或錯誤的 ID。
3.  **上下文摘錄 (Context Extraction)**：
    *   從 `Source Text` 中精確摘錄出支持答案的原文片段，填入 `supporting_context` (List[str])。
4.  **標籤生成 (Tagging)**：
    *   分析題目屬性，生成 `tags` (Dict[str, str])。
    *   格式範例：`{{ "chapter": "工資", "type": "Cross-Document" }}`。

#### 階段三：採樣與推論 (Sampling & Reasoning)
1.  **多樣性採樣**：從優化後的池中挑選 {final_question_count} 題，確保涵蓋不同主題（工資、工時、休假、退休、罰則等）與邏輯類型。
2.  **生成推論 (Reasoning Generation)**：
    *   為入選題目撰寫 `reasoning`。
    *   內容必須解釋：「為什麼這題是 Level 3？」以及「解題的邏輯鏈條是什麼？」。
    *   範例：「需結合 LSA-32 (延長工時規定) 與 LSA-79 (罰則)，單一法條無法得知具體罰鍰金額。」

### 輸出格式 (JSON Format)
請直接輸出一個符合以下 Schema 的 JSON List，不包含 Markdown 標記：

```json
[
    {{
        "question": "具體的情境問題...",
        "ground_truth": "修正後的完整精確答案",
        "reference_articles_id": [["LSA-XX", "ENF-YY"]],
        "supporting_context": [
            "法條A原文片段...",
            "法條B原文片段..."
        ],
        "tags": {{
            "chapter": "主題類別 (如: 工資, 退休)",
            "type": "邏輯類型 (如: Violation+Penalty, Cross-Doc)"
        }},
        "reasoning": "詳細解釋此題的 Multi-hop 邏輯與 RAG 檢索路徑..."
    }}
]
```
---

### 開始生成

請基於以下「「」」中提供的候選問題集 (Candidate Questions)與『』中的法律文本原始資料 (Source Text)，嚴格遵守上述規則與邏輯，進行嚴格審核與增強，最終輸出 {final_question_count} 個高品質題目。

「「
{candidate_questions}
」」

『
{context_law_chunks}
』
"""

# Placeholders for future levels
LEVEL_1_GENERATION_SYSTEM_PROMPT = """
You are an expert legal annotator... (Level 1 Placeholder)
"""

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

        # Select PromptMap
        # Currently we only have Level 3 defined fully as per request,
        # but logic supports branching.
        if "Level 3" in self.target_level:
            self.gen_prompt_template = LEVEL_3_GENERATION_SYSTEM_PROMPT
            self.judge_prompt_template = LEVEL_3_JUDGE_SYSTEM_PROMPT
        else:
            self.gen_prompt_template = LEVEL_1_GENERATION_SYSTEM_PROMPT
            self.judge_prompt_template = (
                LEVEL_3_JUDGE_SYSTEM_PROMPT  # Fallback or defined later
            )

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
        """Creates a generation chain for a single model."""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.gen_prompt_template),
                (
                    "human",
                    "{user_instructions}\n\nPlease start generating the dataset.",
                ),
            ]
        )

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
        judge_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.judge_prompt_template),
                (
                    "human",
                    "{user_instructions}\n\nPlease begin the evaluation process.",
                ),
            ]
        )
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
