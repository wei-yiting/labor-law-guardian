import sys
import argparse
import json
import logging
from pathlib import Path

# Adjust sys.path to ensure absolute imports work from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

# Suppress verbose httpx HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)

from backend.app.rag.config import LATEST_RAG_VERSION
from backend.app.rag.types import RagVersion
from backend.app.rag.version_utils import get_strategy_display_name
from backend.app.rag.factory import get_retriever_strategy
from backend.app.rag.core.evaluation.evaluator import RetrieverEvaluator
from backend.app.rag.core.evaluation.reporting import (
    save_json_log,
    save_text_report,
    print_results,
)


def load_eval_dataset(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Run RAG Evaluation (Refactored)")
    parser.add_argument("--json", action="store_true", help="Generate JSON log file")
    parser.add_argument(
        "--report", action="store_true", help="Generate text report file"
    )
    parser.add_argument("--query", type=str, help="Run a single query check")
    parser.add_argument(
        "--rag-version",
        type=str,
        help=f"Choose RAG Version. Options: {[v.value for v in RagVersion]}",
    )
    parser.add_argument(
        "--incl-tag",
        nargs="+",
        help="Filter dataset to include only items with these tags (OR logic)",
    )
    parser.add_argument(
        "--excl-tag",
        nargs="+",
        help="Filter dataset to exclude items with these tags (OR logic)",
    )

    args = parser.parse_args()

    # 1. Determine Version
    version = args.rag_version if args.rag_version else LATEST_RAG_VERSION

    try:
        rag_version = RagVersion(version)
    except ValueError:
        logger.error(f"Invalid Version '{version}'")
        logger.error(f"Valid versions: {[v.value for v in RagVersion]}")
        sys.exit(1)

    strategy_name = get_strategy_display_name(rag_version)
    logger.info(f"Using RAG Version: {version} ({strategy_name})")

    # 2. Setup Strategy & Evaluator
    try:
        strategy = get_retriever_strategy(version)
        evaluator = RetrieverEvaluator(
            strategy=strategy,
            rag_version=version,
            project_root=str(PROJECT_ROOT),
            use_json_logging=args.json,
        )
    except Exception as e:
        logger.error(f"Failed to initialize RAG components: {e}", exc_info=True)
        sys.exit(1)

    # 3. Interactive Inputs (only if not query mode or verification mode)
    log_prefix = "RTV"
    description = ""
    report_name = "default"

    # Simple check to skip interactivity if running in non-interactive verification
    is_verification = False

    if not args.query:
        if args.json or args.report:
            try:
                logger.info("Experiment Settings")
                # Only ask for log prefix if JSON is enabled, or just keep it simple?
                # The user requirement specifically asked to ensure "Description" is available for Text Reports.
                # JSON log prefix seems specific to JSON filenames.

                if args.json:
                    user_prefix = input(
                        f"Enter JSON log prefix (default: {log_prefix}): "
                    ).strip()
                    if user_prefix == "VERIFY":
                        is_verification = True
                    if user_prefix and not is_verification:
                        log_prefix = user_prefix

                description = input("Enter experiment description (optional): ").strip()
            except KeyboardInterrupt:
                sys.exit(1)
            except EOFError:
                pass  # Piped input might end

    # 4. Execution Mode
    if args.query:
        logger.info(f"Running Single Query: {args.query}")
        nodes = evaluator.run_retrieval(args.query)
        logger.info(f"Retrieved {len(nodes)} nodes")
        for i, node in enumerate(nodes, 1):
            logger.info(f"[{i}] Content: {node.get_content()[:100]}...")
            if hasattr(node, "score"):
                logger.info(f"    Score: {node.score}")
            if node.metadata:
                logger.info(f"    Meta: {node.metadata}")
        return

    # Load Dataset
    dataset_path = PROJECT_ROOT / "backend/data/eval_dataset/master_eval_dataset.json"
    dataset = load_eval_dataset(dataset_path)

    # Filter Dataset
    if args.incl_tag or args.excl_tag:
        original_count = len(dataset)
        incl_tags = set(args.incl_tag) if args.incl_tag else None
        excl_tags = set(args.excl_tag) if args.excl_tag else None

        filtered_dataset = []
        for item in dataset:
            item_tags = set(item.get("tags", []))

            # Tag filtering uses set operations:
            # - Exclusion: Drop item if ANY of its tags match exclusion list (OR logic)
            if excl_tags and not item_tags.isdisjoint(excl_tags):
                continue

            # - Inclusion: Keep item only if it has AT LEAST ONE tag from inclusion list
            if incl_tags:
                if item_tags.isdisjoint(incl_tags):
                    continue

            filtered_dataset.append(item)

        dataset = filtered_dataset
        logger.info(f"Filtered dataset: {len(dataset)} items (Original: {original_count})")

        if not dataset:
            logger.warning("No items found after filtering.")
            sys.exit(0)

    # Smoke Test
    if not evaluator.run_smoke_test(dataset):
        sys.exit(1)

    # Full Evaluation
    logger.info("Running Full Evaluation...")
    results = evaluator.evaluate_dataset(dataset)

    # Print & Save
    print_results(results)

    if args.json:
        save_json_log(results, log_prefix, version, description, str(PROJECT_ROOT))

    if args.report:
        save_text_report(results, version, description, str(PROJECT_ROOT))


if __name__ == "__main__":
    main()
