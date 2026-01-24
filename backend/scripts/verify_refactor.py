import subprocess
import json
import sys
import os
from pathlib import Path

# Snapshot Paths (Relative to Project Root)
SNAPSHOTS = {
    "0.0.1": "backend/experiments/RTV_0.0.1_20260123-154043.json",
    "0.0.2": "backend/experiments/RTV_0.0.2_20260123-154350.json",
    "0.0.3": "backend/experiments/RTV_0.0.3_20260123-154519.json"
}

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_eval(version):
    print(f"Running Eval for {version}...")
    cmd = [
        sys.executable, "backend/scripts/run_eval.py",
        "--json",
        "--rag-version", version
    ]
    # Pipe inputs to skip interactive prompts (Prefix: Enter, Description: Enter)
    process = subprocess.run(cmd, input="VERIFY\nVerification Run\n", text=True, capture_output=True)
    
    if process.returncode != 0:
        print(f"Error running eval for {version} (Exit Code {process.returncode}):")
        print("--- STDOUT ---")
        print(process.stdout)
        print("--- STDERR ---")
        print(process.stderr)
        return None
    
    # Parse stdout to find the output file
    output_lines = process.stdout.splitlines()
    json_path = None
    for line in output_lines:
        if "JSON log saved to:" in line:
            json_path = line.split("JSON log saved to:")[1].strip()
            break
            
    if not json_path:
        print(f"Could not find JSON output path in stdout for {version}")
        print(process.stdout)
        return None
        
    return json_path

def compare_results(version, golden_path, new_path):
    print(f"Comparing {version}...")
    try:
        golden = load_json(golden_path)
        new_res = load_json(new_path)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        return False

    # 1. Compare Overall Score
    g_score = golden['meta']['overall_score']
    n_score = new_res['meta']['overall_score']
    
    if g_score != n_score:
        print(f"❌ Metrics Mismatch for {version}!")
        print(f"   Golden: {g_score}")
        print(f"   New:    {n_score}")
        return False
        
    # 2. Compare Fail Cases Count
    g_cases = golden['fail_cases']
    n_cases = new_res['fail_cases']
    
    if len(g_cases) != len(n_cases):
        print(f"❌ Fail Cases Count Mismatch for {version}!")
        print(f"   Golden: {len(g_cases)}")
        print(f"   New:    {len(n_cases)}")
        return False
        
    # 3. Deep Compare Fail Cases
    # We compare Case ID and Retrieved Content IDs
    print(f"✅ Metrics Match. Deep comparing {len(g_cases)} failure cases...")
    
    mismatch_count = 0
    for i, g_case in enumerate(g_cases):
        n_case = n_cases[i]
        
        if g_case['test_case_id'] != n_case['test_case_id']:
            print(f"   Case Order Mismatch at index {i}")
            mismatch_count += 1
            continue
            
        # Compare Retrieved Nodes
        g_nodes = g_case['retrieval_nodes']
        n_nodes = n_case['retrieval_nodes']
        
        # We check specific keys depending heavily on structure
        # Naive: article_id
        # ParentChild: parent_id, retrieved_chunk_id
        
        if len(g_nodes) != len(n_nodes):
            print(f"   Node Count Mismatch for Case {g_case['test_case_id']}")
            mismatch_count += 1
            continue
            
        for j, g_node in enumerate(g_nodes):
            n_node = n_nodes[j]
            
            # Use loose comparison of relevant keys
            keys_to_check = ['article_id', 'parent_id', 'retrieved_chunk_id']
            for k in keys_to_check:
                if k in g_node:
                    if str(g_node.get(k)) != str(n_node.get(k)):
                         print(f"   Node Mismatch Case {g_case['test_case_id']} Node {j} Key {k}: {g_node.get(k)} != {n_node.get(k)}")
                         mismatch_count += 1
    
    if mismatch_count > 0:
        print(f"❌ Found {mismatch_count} mismatches in content.")
        return False
    
    print(f"✅ {version} Passed Exact Match!")
    return True

def main():
    results = {}
    for version, snapshot in SNAPSHOTS.items():
        print(f"\n--- Verifying {version} ---")
        if not os.path.exists(snapshot):
            print(f"Warning: Snapshot not found for {version} at {snapshot}")
            results[version] = "SKIPPED (No Snapshot)"
            continue
            
        new_json_path = run_eval(version)
        if not new_json_path:
            results[version] = "FAILED (Run Error)"
            continue
            
        passed = compare_results(version, snapshot, new_json_path)
        results[version] = "PASSED" if passed else "FAILED (Mismatch)"
        
        # Cleanup temp file? Maybe keep for detailed inspection if failed.
        
    print("\n" + "="*30)
    print("VERIFICATION SUMMARY")
    print("="*30)
    for v, status in results.items():
        print(f"{v}: {status}")
        
    if all(r == "PASSED" for r in results.values()):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
