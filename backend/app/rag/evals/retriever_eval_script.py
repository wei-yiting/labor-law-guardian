
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Adjust sys.path to ensure absolute imports work from the project root
# This allows 'backend.app...' imports to work regardless of where the script is run from
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.app.rag.retriever.engine import get_retriever
from backend.app.rag.config import RETRIEVER_TOP_K

def load_eval_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_retrieval(retriever, query: str) -> List[Any]:
    return retriever.retrieve(query)

def calculate_metrics(retrieved_nodes, ground_truth_ids: List[str]):
    retrieved_ids = [node.metadata.get("article_id") for node in retrieved_nodes]
    
    # Recall: intersection / len(ground_truth)
    hits = set(retrieved_ids) & set(ground_truth_ids)
    
    if not ground_truth_ids:
        recall = 0.0 # Should not happen in valid dataset
    else:
        recall = len(hits) / len(ground_truth_ids)
    
    # Precision: relevant_retrieved / total_retrieved
    if not retrieved_ids:
        precision = 0.0
    else:
        precision = len(hits) / len(retrieved_ids)
        
    return recall, precision, retrieved_ids

def run_evaluation():
    dataset_path = "backend/data/eval_dataset/master_eval_dataset.json"
    full_dataset_path = PROJECT_ROOT / dataset_path
    
    if not full_dataset_path.exists():
        print(f"Error: Dataset not found at {full_dataset_path}")
        sys.exit(1)
        
    dataset = load_eval_dataset(full_dataset_path)
    
    print("Initializing Retriever...")
    retriever = get_retriever(similarity_top_k=RETRIEVER_TOP_K)
    
    # --- Smoke Test ---
    print("\n" + "="*30)
    print("RUNNING SMOKE TEST")
    print("="*30)
    
    smoke_test_items = [item for item in dataset if "smoke_test" in item.get("tags", [])]
    
    smoke_failed_cases = []
    
    if not smoke_test_items:
        print("Warning: No smoke test items found.")
    
    total_smoke_recall = 0.0
    
    for item in smoke_test_items:
        query = item["question"]
        qid = item["id"]
        gt_ids = item["reference_articles_id"]
        
        nodes = run_retrieval(retriever, query)
        recall, _, retrieved_ids = calculate_metrics(nodes, gt_ids)
        
        total_smoke_recall += recall
        
        # We consider a "Pass" for smoke test if recall is 1.0 (strict) or > 0 ?
        # Usually smoke test expects perfect retrieval for golden cases.
        # But let's check if recall < 1.0 for failure reporting.
        is_hit = recall > 0 # basic hit check, or should we use recall == 1.0?
        # User defined Hit Rate previously as 1 if any hit.
        # New requirement: "recall standard definition".
        # But for smoke test, "hit rate < 60%" blocking condition used hit rate.
        # Let's treat Recall > 0 as a "Hit" for the purpose of the 60% check, 
        # but report failures if Recall < 1.0 for detailed analysis?
        # Requirement: "smoke 與 full eval 如果有 fail 的，應列出 fail 的問題與 問題的 id"
        # "Fail" implies not perfect? Or not finding ANY? 
        # Let's list cases where Recall < 1.0 (missing some GT) as "Optimization needed",
        # but for Smoke Test "Failure" usually means Recall = 0 (Total miss).
        # Let's list Recall < 1.0 cases for visibility.
        
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

    # Smoke Test Check
    # The requirement said "IF Smoke Test fails significantly (e.g., < 60% hit rate), STOP".
    # Hit Rate typically means "At least one relevant doc retrieved". 
    # Let's stick to Average Recall for general metrics, but check Blocking condition based on "At least one hit".
    
    smoke_hits = sum(1 for item in smoke_failed_cases if item['recall'] > 0) + (len(smoke_test_items) - len(smoke_failed_cases))
    # Wait, simple logic: count items where recall > 0
    smoke_hit_count = 0
    for item in smoke_test_items:
         # We need to re-run or store result? 
         # Ah, I didn't store all results clearly. 
         # Let's just use the `total_smoke_recall / len` as a proxy, 
         # or simply count successful items (Recall > 0)
         pass 

    # Re-evaluating blocking logic:
    # Let's use Average Recall for the 60% threshold? Or strict hit rate?
    # User said: "calculate metrics ... Recall (Hit Rate)".
    # User comment: "Recall ... intersection/ground_truth ... 0 to 1".
    # So "Hit Rate" now becomes "Average Recall".
    
    avg_smoke_recall = total_smoke_recall / len(smoke_test_items) if smoke_test_items else 0.0
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
        sys.exit(1)
        
    print("Smoke Test Passed.")
    
    # --- Full Evaluation ---
    print("\n" + "="*30)
    print("RUNNING FULL EVALUATION")
    print("="*30)
    
    total_items = len(dataset)
    total_recall = 0.0
    total_precision = 0.0
    full_failed_cases = []
    
    for i, item in enumerate(dataset):
        query = item["question"]
        qid = item["id"]
        gt_ids = item["reference_articles_id"]
        supporting_context = item.get("supporting_context", "N/A")
        reasoning = item.get("reasoning", "N/A")
        
        nodes = run_retrieval(retriever, query)
        recall, precision, retrieved_ids = calculate_metrics(nodes, gt_ids)
        
        total_recall += recall
        total_precision += precision
        
        if recall < 1.0:
             full_failed_cases.append({
                "id": qid,
                "question": query,
                "recall": recall,
                "gt": gt_ids,
                "retrieved": retrieved_ids,
                "supporting_context": supporting_context,
                "reasoning": reasoning
            })
        
        if (i + 1) % 10 == 0:
            print(f"Processed {i + 1}/{total_items} queries...")
            
    avg_recall = total_recall / total_items
    avg_precision = total_precision / total_items
    
    print("\n" + "="*30)
    print("EVALUATION RESULTS")
    print("="*30)
    print(f"Total Queries: {total_items}")
    print(f"Average Recall: {avg_recall:.4f}")
    print(f"Average Precision: {avg_precision:.4f}")
    
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
    
    # Simple report file
    report_path = PROJECT_ROOT / "backend/rag_baseline_report.txt"
    with open(report_path, "w") as f:
        f.write("Naive RAG Baseline Evaluation Report\n")
        f.write(f"Average Recall: {avg_recall:.4f}\n")
        f.write(f"Average Precision: {avg_precision:.4f}\n")
        f.write(f"Config: top_k={RETRIEVER_TOP_K}\n")
        
        if full_failed_cases:
            f.write("\nFailed Cases (Recall < 1.0):\n")
            for case in full_failed_cases:
                f.write(f"[{case['id']}] {case['question']}\n")
                f.write(f"  Recall: {case['recall']:.2f}\n")
                f.write(f"  GT: {case['gt']}\n")
                f.write(f"  Retrieved: {case['retrieved']}\n")
                f.write(f"  Context: {case['supporting_context']}\n")
                f.write(f"  Reasoning: {case['reasoning']}\n")
                f.write("-" * 20 + "\n")

if __name__ == "__main__":
    run_evaluation()
