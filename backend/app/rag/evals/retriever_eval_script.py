
import json
import sys
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Adjust sys.path to ensure absolute imports work from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Import config and engine
from backend.app.rag.retriever.engine import get_retriever
from backend.app.rag.config import (
    RETRIEVER_TOP_K, 
    OPENAI_MODEL_NAME, 
    EMBEDDING_MODEL_NAME, 
    CHUNK_SIZE
)
from backend.app.rag.evals.law_lookup import LawLookup

class RetrieverEvaluator:
    def __init__(self, use_json_logging: bool = False):
        print("Initializing Retriever...")
        self.retriever = get_retriever(similarity_top_k=RETRIEVER_TOP_K)
        self.use_json_logging = use_json_logging
        self.law_lookup = LawLookup(PROJECT_ROOT) if use_json_logging else None

    def run_retrieval(self, query: str) -> List[Any]:
        return self.retriever.retrieve(query)

    def calculate_metrics(self, retrieved_nodes, ground_truth_ids: List[str]) -> Tuple[float, float, List[str]]:
        retrieved_ids = [node.metadata.get("article_id") for node in retrieved_nodes]
        
        # Recall: intersection / len(ground_truth)
        hits = set(retrieved_ids) & set(ground_truth_ids)
        
        if not ground_truth_ids:
            recall = 0.0
        else:
            recall = len(hits) / len(ground_truth_ids)
        
        # Precision: relevant_retrieved / total_retrieved
        if not retrieved_ids:
            precision = 0.0
        else:
            precision = len(hits) / len(retrieved_ids)
            
        return recall, precision, retrieved_ids

    def evaluate_single_query(self, query: str):
        print(f"\nRunning Single Query: {query}")
        nodes = self.run_retrieval(query)
        print(f"Retrieved {len(nodes)} nodes:\n")
        for i, node in enumerate(nodes, 1):
            aid = node.metadata.get("article_id", "N/A")
            score = node.score if hasattr(node, "score") else "N/A"
            print(f"[{i}] ID: {aid} | Score: {score}")
            print(f"    Content: {node.text}" if node.text else "    Content: N/A")
            print("-" * 40)

    def run_smoke_test(self, dataset: List[Dict[str, Any]]) -> bool:
        print("\n" + "="*30)
        print("RUNNING SMOKE TEST")
        print("="*30)
        
        smoke_test_items = [item for item in dataset if "smoke_test" in item.get("tags", [])]
        smoke_failed_cases = []
        
        if not smoke_test_items:
            print("Warning: No smoke test items found.")
            return True # No smoke tests to fail
        
        total_smoke_recall = 0.0
        
        for item in smoke_test_items:
            query = item["question"]
            qid = item["id"]
            gt_ids = item["reference_articles_id"]
            
            nodes = self.run_retrieval(query)
            recall, _, retrieved_ids = self.calculate_metrics(nodes, gt_ids)
            
            total_smoke_recall += recall
            
            status = "PASS" if recall == 1.0 else ("PARTIAL" if recall > 0 else "FAIL")
            print(f"[{status}] {qid}: {query[:30]}... | GT: {gt_ids} | Retrieved: {retrieved_ids} | Recall: {recall:.2f}")
            
            if recall < 1.0:
                smoke_failed_cases.append({
                    "id": qid,
                    "question": query,
                    "recall": recall,
                    "gt": gt_ids,
                    "retrieved": retrieved_ids
                })

        avg_smoke_recall = total_smoke_recall / len(smoke_test_items)
        print(f"\nSmoke Test Average Recall: {avg_smoke_recall:.2%}")

        if smoke_failed_cases:
            print("\n[Smoke Test Failures / Imperfect Retrievals]")
            for case in smoke_failed_cases:
                 print(f" - ID: {case['id']}")
                 print(f"   Question: {case['question']}")
                 print(f"   Expected: {case['gt']}")
                 print(f"   Got: {case['retrieved']}")
                 print(f"   Recall: {case['recall']:.2f}")
                 print("")

        if avg_smoke_recall < 0.6:
            print("CRITICAL: Smoke Test Average Recall < 60%. Aborting Full Evaluation.")
            return False
            
        print("Smoke Test Passed.")
        return True

    def run_full_evaluation(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        print("\n" + "="*30)
        print("RUNNING FULL EVALUATION")
        print("="*30)
        
        total_recall = 0.0
        total_precision = 0.0
        full_failed_cases = [] # Simple list for stdout report
        fail_cases_data = []   # Detailed list for JSON log
        
        total_items = len(dataset)
        
        for i, item in enumerate(dataset):
            query = item["question"]
            qid = item["id"]
            gt_ids = item["reference_articles_id"]
            supporting_context = item.get("supporting_context", "N/A")
            reasoning = item.get("reasoning", "N/A")
            
            nodes = self.run_retrieval(query)
            recall, precision, retrieved_ids = self.calculate_metrics(nodes, gt_ids)
            
            total_recall += recall
            total_precision += precision
            
            if recall < 1.0:
                # For stdout report
                full_failed_cases.append({
                    "id": qid,
                    "question": query,
                    "recall": recall,
                    "gt": gt_ids,
                    "retrieved": retrieved_ids,
                    "supporting_context": supporting_context,
                    "reasoning": reasoning
                })
                
                # For JSON Log (if enabled)
                if self.use_json_logging and self.law_lookup:
                    # 1. Build Ground Truth Docs
                    gt_docs = []
                    for art_id in gt_ids:
                        article = self.law_lookup.get_article(art_id)
                        content = article.get("content", "") if article else "Content not found"
                        gt_docs.append({
                            "article_id": art_id,
                            "content": content
                        })
                    
                    # 2. Build Retrieval Nodes
                    retrieved_nodes_data = []
                    for node in nodes:
                        node_aid = node.metadata.get("article_id", "Unknown")
                        node_content = node.text or "" 
                        retrieved_nodes_data.append({
                            "article_id": node_aid,
                            "content": node_content
                        })

                    case_data = {
                        "test_case_id": qid,
                        "question": query,
                        "ground_truth_documents": gt_docs,
                        "retrieval_nodes": retrieved_nodes_data,
                        "judge_feedback": [],
                        "possible_resolution": []
                    }
                    fail_cases_data.append(case_data)
            
            if (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{total_items} queries...")

        avg_recall = total_recall / total_items if total_items > 0 else 0
        avg_precision = total_precision / total_items if total_items > 0 else 0
        
        # Determine results
        results = {
            "total_items": total_items,
            "avg_recall": avg_recall,
            "avg_precision": avg_precision,
            "full_failed_cases": full_failed_cases,
            "fail_cases_data": fail_cases_data
        }
        
        return results

    def print_results(self, results: Dict[str, Any]):
        print("\n" + "="*30)
        print("EVALUATION RESULTS")
        print("="*30)
        print(f"Total Queries: {results['total_items']}")
        print(f"Average Recall: {results['avg_recall']:.4f}")
        print(f"Average Precision: {results['avg_precision']:.4f}")
        
        full_failed_cases = results.get("full_failed_cases", [])
        if full_failed_cases:
            print("\n" + "="*30)
            print("FAILED CASES (Recall < 1.0)")
            print("="*30)
            for case in full_failed_cases:
                 print(f"ID: {case['id']} | Recall: {case['recall']:.2f}")
                 print(f"Q: {case['question']}")
                 print(f"GT: {case['gt']} | Retrieved: {case['retrieved']}")
                 print(f"Context: {case['supporting_context']}")
                 print(f"Reasoning: {case['reasoning']}")
                 print("-" * 20)

def load_eval_dataset(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_log(results: Dict[str, Any], log_prefix: str, version: str):
    now = datetime.datetime.now()
    timestamp_str = now.isoformat()
    # Format: 20260121-155020
    date_seq = now.strftime("%Y%m%d-%H%M%S")
    
    # Construct Run ID / Filename portion
    # User requested format: RTV_0.0.1_20260121-155020.json
    run_id = f"{log_prefix}_{version}_{date_seq}"
    
    output_data = {
        "meta": {
            "run_id": run_id,
            "timestamp": timestamp_str,
            "agent_version": version,
            "configuration": {
                "strategy": "",
                "tokenizer": OPENAI_MODEL_NAME,
                "embedding": EMBEDDING_MODEL_NAME,
                "chunk_size": CHUNK_SIZE,
                "top_k": RETRIEVER_TOP_K
            },
            "data": {
                "eval_datasets": [],
                "source_documents": []
            },
            "overall_score": {
                "average_recall": round(results['avg_recall'], 4),
                "average_precision": round(results['avg_precision'], 4)
            }
        },
        "fail_cases": results.get('fail_cases_data', [])
    }
    
    output_dir = PROJECT_ROOT / "backend/experiments"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{run_id}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nJSON log saved to: {output_file}")

def save_text_report(results: Dict[str, Any], report_name: str):
    # Construct filename: {report_name}_eval_report.txt
    filename = f"{report_name}_eval_report.txt"
    output_dir = PROJECT_ROOT / "backend/app/rag/evals/reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / filename
    
    avg_recall = results['avg_recall']
    avg_precision = results['avg_precision']
    full_failed_cases = results.get("full_failed_cases", [])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Naive RAG Baseline Evaluation Report\n")
        f.write(f"Average Recall: {avg_recall:.4f}\n")
        f.write(f"Average Precision: {avg_precision:.4f}\n")
        f.write(f"Config: top_k={RETRIEVER_TOP_K}\n")
        
        if full_failed_cases:
            f.write("\nFailed Cases (Recall < 1.0):\n")
            for case in full_failed_cases:
                f.write(f"[{case['id']}] {case['question']}\n")
                f.write(f"  Recall: {case['recall']:.2f}\n")
                f.write("-" * 20 + "\n")
                
    print(f"\nText report saved to: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Run Retriever Evaluation")
    parser.add_argument("--json", action="store_true", help="Generate JSON log file in backend/experiments")
    parser.add_argument("--report", action="store_true", help="Generate text report file in backend/app/rag/evals/reports")
    parser.add_argument("--query", type=str, help="Run a single query check and exit")
    args = parser.parse_args()
    
    # Interactive Input for JSON Log Naming
    log_prefix = "RTV"
    version = "0.0.1"
    
    # Interactive Input for Text Report Naming
    report_name = "default"

    if args.json:
        try:
            print("\n--- JSON Log Settings ---")
            user_prefix = input("Enter log prefix (default: RTV): ").strip()
            if user_prefix:
                log_prefix = user_prefix
            
            user_version = input("Enter version (default: 0.0.1): ").strip()
            if user_version:
                version = user_version
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(1)
            
    if args.report:
        try:
            print("\n--- Text Report Settings ---")
            user_report_name = input("Enter report name (default: default): ").strip()
            if user_report_name:
                report_name = user_report_name
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(1)
    
    # Setup Evaluator
    evaluator = RetrieverEvaluator(use_json_logging=args.json)

    # 1. Single Query Mode
    if args.query:
        evaluator.evaluate_single_query(args.query)
        return

    # Load Data
    dataset_path = PROJECT_ROOT / "backend/data/eval_dataset/master_eval_dataset.json"
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        sys.exit(1)
    
    dataset = load_eval_dataset(dataset_path)

    # 2. Smoke Test
    if not evaluator.run_smoke_test(dataset):
        sys.exit(1)

    # 3. Full Evaluation
    results = evaluator.run_full_evaluation(dataset)
    
    # 4. Print Results
    evaluator.print_results(results)

    # 5. JSON Logging
    if args.json:
        save_json_log(results, log_prefix, version)
        
    # 6. Text Report Generation
    if args.report:
        save_text_report(results, report_name)

if __name__ == "__main__":
    main()
