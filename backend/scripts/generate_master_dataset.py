"""
Generate Master Dataset Script

This script incrementally updates the master evaluation dataset by merging a new subset JSON file.
It performs the following operations:
1. Loads the existing master dataset.
2. Reads the new subset file.
3. Assigns unique semantic IDs to new questions based on their topic and sequence.
4. Generates tags (Level, Topic, Type, Smoke Test).
5. Validates immutability of existing data and schema compliance of new data.
6. Saves the updated master dataset to `backend/data/eval_dataset/master_eval_dataset.json`.

Usage:
    Run this script from the project root directory.

    uv run -m backend.scripts.generate_master_dataset --input_file <path_to_subset_json> --level <dataset_level>

Arguments:
    --input_file: Path to the new subset JSON file containing questions to add.
    --level:      Integer representing the difficulty level of the dataset (e.g., 1, 2).

Example:
    uv run -m backend.scripts.generate_master_dataset --input_file backend/data/eval_dataset/subset/level2_tier1_dataset.json --level 2
"""

import json
import re
import os
import argparse
import copy
from collections import defaultdict

from pathlib import Path

# --- Configuration ---
# Resolve paths relative to the project root (assuming script is in backend/scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
MASTER_FILE = PROJECT_ROOT / "backend/data/eval_dataset/master_eval_dataset.json"
SUBSET_DIR = PROJECT_ROOT / "backend/data/eval_dataset/subset"

TOPIC_MAPPING = {
    "工資": "WAGE",
    "勞動契約": "CNTR",
    "工作時間": "TIME",
    "工作時間、休息、休假": "TIME",
    "退休": "RETIRE",
    "職業災害補償": "INJR",
    "職災補償": "INJR",
    "童工、女工": "FEM",
    "技術生": "APPR",
    "工作規則": "RULE",
    "監督與檢查": "INSP",
    "假別與日數": "LEAVE",
    "工資與權益": "WAGE",
    "請假流程": "LEAVE",
    "休假": "LEAVE",
    "工時": "TIME",
    "職業災害": "INJR",
    "總則": "GEN",
    "罰則": "PEN",
    # Add English mappings for convenience if input file already uses codes, or specific specialized topics
}

SMOKE_TEST_QUESTIONS = {
    "勞工正常工作時間，每日及每週之最高限度分別為何？",
    "勞工結婚者，應給予婚假幾日？",
    "積欠工資墊償基金之費率，由中央主管機關於多少範圍內擬訂？",
    "勞動契約中的「臨時性工作」是如何定義的？其工作期間上限為多久？",
    "技術生是否可以從事事業場所內的清潔整頓工作？",
}


def generate_semantic_id(level, topic_code, seq_num):
    return f"L{level}-{topic_code}-{seq_num:03d}"


def generate_tags(level, topic_code, type_str, question_text):
    tags = [f"level_{level}"]

    # Topic Tag
    tags.append(f"topic_{topic_code.lower()}")

    # Type Tag
    if type_str:
        normalized_type = type_str.lower().replace(" ", "_").replace("/", "_")
        tags.append(f"type_{normalized_type}")

    # Smoke Test Tag
    if question_text in SMOKE_TEST_QUESTIONS:
        tags.append("smoke_test")
    return tags


def load_json(path):
    if not os.path.exists(path):
        print(f"WARNING: File not found at {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="Incrementally update master eval dataset."
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Filename of the new subset JSON file (relative to backend/data/eval_dataset/subset).",
    )
    parser.add_argument(
        "--level", type=int, required=True, help="Level of the dataset (e.g., 1, 2)."
    )
    args = parser.parse_args()

    print("--- Starting Update Process ---")

    # Resolve input file path
    # Priority 1: Check in SUBSET_DIR (User preferred)
    input_path = SUBSET_DIR / args.input_file

    if not input_path.exists():
        # Priority 2: Check relative to Project Root
        potential_path = PROJECT_ROOT / args.input_file
        if potential_path.exists():
            input_path = potential_path
        else:
            # Priority 3: Check as absolute/relative to CWD
            potential_path = Path(args.input_file)
            if potential_path.exists():
                input_path = potential_path

    print(f"Input File: {input_path}")
    print(f"Level: {args.level}")

    # 1. Load Master Dataset
    master_data = load_json(MASTER_FILE)
    original_master_data = copy.deepcopy(master_data)  # For Immutability Check
    print(f"Loaded Master Dataset: {len(master_data)} items")

    # 2. Analyze State
    existing_questions = {item["question"]: item for item in master_data}
    existing_ids = {item["id"] for item in master_data}

    # Calculate max SEQ per topic across ALL levels
    # Pattern: L{LEVEL}-{TOPIC}-{SEQ}
    topic_max_counters = defaultdict(int)
    id_pattern = re.compile(r"^L\d+-([A-Z]+)-(\d{3})$")

    for item in master_data:
        match = id_pattern.match(item["id"])
        if match:
            topic = match.group(1)
            seq = int(match.group(2))
            topic_max_counters[topic] = max(topic_max_counters[topic], seq)

    # 3. Process Input
    subset_data = load_json(input_path)
    print(f"Loaded Input Subset: {len(subset_data)} items")

    added_count = 0
    skipped_count = 0

    # For Mapping Consistency Check later
    new_subset_map = {}

    for item in subset_data:
        question = item.get("question")
        chapter = item.get("tags", {}).get("chapter")
        type_str = item.get("tags", {}).get("type")
        ref_ids = item.get("reference_articles_id", [])
        ground_truth = item.get("ground_truth")

        # Store for consistency check
        new_subset_map[question] = {"ref_ids": ref_ids, "ground_truth": ground_truth}

        if question in existing_questions:
            print(f"DEBUG: Skipping existing question: {question[:30]}...")
            skipped_count += 1
            continue

        if not chapter or chapter not in TOPIC_MAPPING:
            print(
                f"Warning: Unknown or missing chapter mapping for '{chapter}'. Skipping item: {question}"
            )
            continue

        topic_code = TOPIC_MAPPING[chapter]

        # Increment Counter
        topic_max_counters[topic_code] += 1
        current_seq = topic_max_counters[topic_code]

        semantic_id = generate_semantic_id(args.level, topic_code, current_seq)
        if semantic_id in existing_ids:
            raise ValueError(
                f"CRITICAL ERROR: Generated ID {semantic_id} already exists! Counter logic is flawed."
            )

        tags = generate_tags(args.level, topic_code, type_str, question)

        new_item = {
            "id": semantic_id,
            "question": question,
            "ground_truth": ground_truth,
            "reference_articles_id": ref_ids,
            "supporting_context": item.get("supporting_context"),
            "tags": tags,
            "reasoning": item.get("reasoning"),
        }

        master_data.append(new_item)
        added_count += 1

    print(f"Processing Complete. Added: {added_count}, Skipped: {skipped_count}")

    # --- Validation ---
    print("\n--- Running Validations ---")

    # 1. Immutability Check
    # Verify that all items from the original master data are still present and unchanged in the new master data
    print("1. Executing Immutability Check...")
    new_master_map = {item["id"]: item for item in master_data}

    for original_item in original_master_data:
        item_id = original_item["id"]
        if item_id not in new_master_map:
            raise AssertionError(
                f"Immutability Failed: Item {item_id} missing in new dataset."
            )

        # Verify exact dictionary equality for immutability check
        if original_item != new_master_map[item_id]:
            raise AssertionError(
                f"Immutability Failed: Item {item_id} has been modified."
            )
    print("PASS: Immutability Check")

    # 2. Schema Check (for newly added items)
    print("2. Executing Schema Check...")
    for item in master_data:
        # Check newly generated IDs only, or check all to be safe. checking all.
        match = id_pattern.match(item["id"])
        if not match:
            raise AssertionError(f"Schema Failed: Invalid ID format {item['id']}")

        # Check L{Level} tag
        level_tag = f"level_{args.level}"
        # Only check level tag for items that "appear" to be from this level based on ID
        if item["id"].startswith(f"L{args.level}-"):
            if level_tag not in item["tags"]:
                raise AssertionError(
                    f"Schema Failed: Item {item['id']} missing tag {level_tag}"
                )
    print("PASS: Schema Check")

    # 3. Mapping Consistency Check
    # Ensure that for every question in the input subset, the final master dataset has the EXACT same ref_ids and ground_truth
    print("3. Executing Mapping Consistency Check...")
    final_question_map = {item["question"]: item for item in master_data}

    for q, source_vals in new_subset_map.items():
        if q not in final_question_map:
            # Should practically never happen unless logic error above
            raise AssertionError(
                f"Consistency Failed: Question not found in master dataset: {q}"
            )

        final_item = final_question_map[q]

        # Check Reference IDs
        if final_item["reference_articles_id"] != source_vals["ref_ids"]:
            raise AssertionError(
                f"Consistency Failed: Ref IDs mismatch for '{q}'.\nExpected: {source_vals['ref_ids']}\nActual: {final_item['reference_articles_id']}"
            )

        # Validate Ground Truth consistency
        if final_item["ground_truth"] != source_vals["ground_truth"]:
            # Defer validation to the final consistency check loop
            pass

    # Verify data consistency across all items (new and existing)
    # Ensures that the Master dataset aligns with the input subset for critical fields.

    for q, source_vals in new_subset_map.items():
        final_item = final_question_map[q]
        if final_item["reference_articles_id"] != source_vals["ref_ids"]:
            print(
                f"WARNING: Consistency Conflict for Existing Item '{q}'. Master has different Ref IDs than Input."
            )
            # Prioritize existing Master data over Input for conflicts, but strictly enforce consistency for new items.
            if final_item["id"].startswith(f"L{args.level}-"):  # Heuristic for new item
                raise AssertionError(
                    f"Consistency Failed New Item: Ref IDs mismatch for '{q}'"
                )

        if final_item["ground_truth"] != source_vals["ground_truth"]:
            if final_item["id"].startswith(f"L{args.level}-"):
                raise AssertionError(
                    f"Consistency Failed New Item: Ground Truth mismatch for '{q}'"
                )

    print("PASS: Mapping Consistency Check")

    # --- Write Output ---
    save_json(MASTER_FILE, master_data)
    print(f"SUCCESS: Master dataset updated at {MASTER_FILE}")


if __name__ == "__main__":
    main()
