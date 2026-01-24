import sys
import argparse
import json
from pathlib import Path

# Adjust sys.path to ensure absolute imports work from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Imports
from backend.app.rag.config import RAG_VERSIONS, LATEST_RAG_VERSION
from backend.app.rag.factory import get_retriever_strategy
from backend.app.rag.core.evaluation.evaluator import RetrieverEvaluator
from backend.app.rag.core.evaluation.reporting import save_json_log, save_text_report, print_results

def load_eval_dataset(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="Run RAG Evaluation (Refactored)")
    parser.add_argument("--json", action="store_true", help="Generate JSON log file")
    parser.add_argument("--report", action="store_true", help="Generate text report file")
    parser.add_argument("--query", type=str, help="Run a single query check")
    parser.add_argument("--rag-version", type=str, help=f"Choose RAG Version. Options: {list(RAG_VERSIONS.keys())}")
    
    args = parser.parse_args()
    
    # 1. Determine Version
    version = args.rag_version if args.rag_version else LATEST_RAG_VERSION
    if version not in RAG_VERSIONS:
        print(f"Error: Invalid Version '{version}'")
        sys.exit(1)
    
    print(f"Using RAG Version: {version} ({RAG_VERSIONS[version]})")
    
    # 2. Setup Strategy & Evaluator
    try:
        strategy = get_retriever_strategy(version)
        evaluator = RetrieverEvaluator(
            strategy=strategy, 
            rag_version=version, 
            project_root=str(PROJECT_ROOT),
            use_json_logging=args.json
        )
    except Exception as e:
        print(f"Failed to initialize RAG components: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 3. Interactive Inputs (only if not query mode or verification mode)
    log_prefix = "RTV"
    description = ""
    report_name = "default"
    
    # Simple check to skip interactivity if running in non-interactive verification
    is_verification = False
    
    if not args.query:
        if args.json:
            try:
                # Basic check if input is piped or tty, but verification script pipes input anyway.
                print("\n--- JSON Log Settings ---")
                user_prefix = input(f"Enter log prefix (default: {log_prefix}): ").strip()
                if user_prefix == "VERIFY": is_verification = True
                if user_prefix and not is_verification: log_prefix = user_prefix
                
                description = input("Enter experiment description (optional): ").strip()
            except KeyboardInterrupt:
                sys.exit(1)
            except EOFError:
                pass # Piped input might end
                
        if args.report:
            try:
                print("\n--- Text Report Settings ---")
                user_name = input("Enter report name (default: default): ").strip()
                if user_name: report_name = user_name
            except KeyboardInterrupt:
                sys.exit(1)
            except EOFError:
                pass

    # 4. Execution Mode
    if args.query:
        print(f"\nRunning Single Query: {args.query}")
        nodes = evaluator.run_retrieval(args.query)
        print(f"Retrieved {len(nodes)} nodes:\n")
        for i, node in enumerate(nodes, 1):
             print(f"[{i}] Content: {node.get_content()[:100]}...")
             if hasattr(node, "score"): print(f"    Score: {node.score}")
             if node.metadata: print(f"    Meta: {node.metadata}")
        return

    # Load Dataset
    dataset_path = PROJECT_ROOT / "backend/data/eval_dataset/master_eval_dataset.json"
    dataset = load_eval_dataset(dataset_path)

    # Smoke Test
    if not evaluator.run_smoke_test(dataset):
        sys.exit(1)

    # Full Evaluation
    print("\nRunning Full Evaluation...")
    results = evaluator.evaluate_dataset(dataset)
    
    # Print & Save
    print_results(results)
    
    if args.json:
        save_json_log(results, log_prefix, version, description, str(PROJECT_ROOT))
    
    if args.report:
        save_text_report(results, report_name, str(PROJECT_ROOT))

if __name__ == "__main__":
    main()
