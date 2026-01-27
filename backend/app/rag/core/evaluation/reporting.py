import json
import datetime
import re
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
    
    # Dynamically extract scores
    score_metrics = {
        k: round(v, 4) for k, v in results.items() 
        if k.startswith(("avg_recall@", "avg_precision@", "MAP@", "MRR@"))
    }

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
                "source_documents": [],
                "total_queries": results["total_items"]
            },
            "overall_score": score_metrics
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


def save_text_report(results: Dict[str, Any], version: str, description: str, project_root: str):
    project_root_path = Path(project_root)
    output_dir = project_root_path / "backend/experiments"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "consolidated_eval_report.md"
    
    # Generate the new block content
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Format the metrics
    metrics_str = ""
    metrics = [k for k in results.keys() if k.startswith(("avg_recall@", "avg_precision@", "MAP@", "MRR@"))]
    for key in sorted(metrics):
        metrics_str += f"- **{key}**: {results[key]:.4f}\n"

    failed_cases_str = ""
    full_failed_cases = results.get("full_failed_cases", [])
    if full_failed_cases:
        failed_cases_str += "\n### Failed Cases (Recall < 1.0)\n"
        for case in full_failed_cases:
            failed_cases_str += f"- **[{case['id']}]** {case['question']}\n"
            failed_cases_str += f"  - Recall: {case['recall']:.2f}\n"

    new_block = f"""## Version {version}

### Metadata
- **Datetime**: {timestamp_str}
- **Description**: {description}

### Metrics
- **Total Queries**: {results['total_items']}
{metrics_str}- **Config**: top_k={RETRIEVER_TOP_K}
{failed_cases_str}
### Manual Analysis
- **Error analysis**: 
- **Possible resolution**: 
- **Has implemented possible resolution**: 
- **Has failures fixed**: 
"""

    if not report_path.exists():
        content = new_block
    else:
        content = report_path.read_text(encoding="utf-8")
        
        # Regex to find existing block for this version
        # Header pattern: ## Version 0.0.1
        # Lookahead: Next "## Version " or End of File
        header_pattern = rf"## Version {re.escape(version)}"
        next_header_lookahead = rf"(?=\n## Version |\Z)"
        
        # Note: We need to match newline before ## Version to correctly identify start if it's not the first line,
        # but the first line won't have a newline before it.
        # However, our regex search finds the first match.
        # Safe strategy: Match literal "## Version X" at start of line (multiline).
        # We use re.M (multiline) but re.DOTALL makes . match newlines.
        
        # Let's stick to constructed pattern.
        # We want to capture the whole block.
        # Start: "## Version {version}"
        # End: Start of next "## Version" or EOF.
        
        pattern = re.compile(rf"(^## Version {re.escape(version)}.*?{next_header_lookahead})", re.DOTALL | re.MULTILINE)
        
        match = pattern.search(content)
        if match:
            # Replace existing block
            start, end = match.span()
            content = content[:start] + new_block.strip() + content[end:]
        else:
            # Append new block
            if content and not content.endswith("\n"):
                content += "\n"
            
            if not content.strip(): 
                # If file is logically empty
                content = new_block
            else:
                # Append three newlines for separation between blocks
                content = content.rstrip() + "\n\n\n\n" + new_block
            
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"\nText report saved to: {report_path}")

def print_results(results: Dict[str, Any]):
    print("\n" + "="*30)
    print("EVALUATION RESULTS")
    print("="*30)
    print(f"Total Queries: {results['total_items']}")
    
    # Dynamically print metrics
    metrics = [k for k in results.keys() if k.startswith(("avg_recall@", "avg_precision@", "MAP@", "MRR@"))]
    for key in sorted(metrics):
        print(f"{key:<20}: {results[key]:.4f}")
    
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
