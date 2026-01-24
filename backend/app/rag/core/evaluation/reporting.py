import json
import datetime
from pathlib import Path
from typing import Dict, Any, List
from backend.app.rag.config import (
    RAG_VERSIONS, OPENAI_MODEL_NAME, EMBEDDING_MODEL_NAME, CHUNK_SIZE, RETRIEVER_TOP_K
)

def save_json_log(results: Dict[str, Any], log_prefix: str, version: str, description: str, project_root: str):
    now = datetime.datetime.now()
    timestamp_str = now.isoformat()
    date_seq = now.strftime("%Y%m%d-%H%M%S")
    
    run_id = f"{log_prefix}_{version}_{date_seq}"
    
    output_data = {
        "meta": {
            "run_id": run_id,
            "timestamp": timestamp_str,
            "description": description,
            "agent_version": version,
            "configuration": {
                "rag_version": version,
                "strategy": RAG_VERSIONS.get(version, "UNKNOWN"),
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
    
    project_root_path = Path(project_root)
    output_dir = project_root_path / "backend/experiments"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{run_id}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nJSON log saved to: {output_file}")


def save_text_report(results: Dict[str, Any], report_name: str, project_root: str):
    base_name = f"{report_name}_eval_report.txt"
    project_root_path = Path(project_root)
    output_dir = project_root_path / "backend/app/rag/evals/reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / base_name
    
    avg_recall = results['avg_recall']
    avg_precision = results['avg_precision']
    full_failed_cases = results.get("full_failed_cases", [])

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("RAG Evaluation Report\n")
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

def print_results(results: Dict[str, Any]):
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
            # Safely access keys that might not be in every dict if structure changed, 
            # but our Evaluator produces them.
            print(f"ID: {case.get('id')} | Recall: {case.get('recall', 0.0):.2f}")
            print(f"Q: {case.get('question')}")
            # print(f"GT: {case['gt']} | Retrieved: {case['retrieved']}")
            # Context is usually too long to print everything
            print("-" * 20)
