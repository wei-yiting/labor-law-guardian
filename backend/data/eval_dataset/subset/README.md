# RAG Evaluation Dataset Subsets

This directory stores the modular subset files that comprise the RAG Evaluation Dataset ecosystem. These files serve as the building blocks for the Master Dataset.

## 📂 Folder Responsibility

- **Data Modularity**: Break down the large evaluation dataset into manageable, logic-specific files (Subsets).
- **Difficulty Tiering**: Organize test cases by complexity (Levels) and quality tiers (Tier 1, 2, etc.).
- **Incremental Build**: New test cases are added here first before being merged into the master dataset.

## 🗂 File Manifest

File Naming Standard: `level{N}_tier{M}_dataset.json`

| Filename                     | Description                                                                                                                                                 |
| :--------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `level1_tier1_dataset.json`  | **Single-Hop / Fact Retrieval**.<br>Core test cases where answers are explicitly stated in a single legal article. Tests basic retriever precision.         |
| `level_3_tier1_dataset.json` | **Multi-Hop / Reasoning**.<br>Advanced test cases requiring the synthesis of information from multiple articles (e.g., linking a Prohibition to a Penalty). |

## 🏗 Architecture (Schema)

All JSON files in this directory adhere to the following `EvalDatasetItem` schema:

```json
[
  {
    "question": "Specific scenario question (String)",
    "ground_truth": "Standard verification answer (String)",
    "reference_articles_id": [
      ["LSA-11", "LSA-16"]
      // List of Lists. Each inner list represents a sufficient set of Article IDs (Parent IDs).
    ],
    "supporting_context": [
      "Original article snippet A...",
      "Original article snippet B..."
    ],
    "tags": {
      "chapter": "Legal Chapter (e.g., Wages, Retirement)",
      "type": "Logic Type (e.g., Definition, Cross-Reference)"
    },
    "reasoning": "Explanation of the retrieval logic required to answer this question."
  }
]
```

## 🚀 Usage Guidelines

1.  **Adding Data**:
    - Use `backend/scripts/generate_eval_dataset.py` to generate new subsets.
    - Do not manually edit large JSON files to avoid schema corruption.

2.  **Merging Data**:
    - Use `backend/scripts/generate_master_dataset.py` to merge these subsets into the `master_eval_dataset.json`.

3.  **Versioning**:
    - **Level 1**: Basic facts, definitions, and direct lookups.
    - **Level 3**: Cross-document referencing and complex logic.
    - **Tier 1**: High-confidence, manually verified or high-consensus data.
    - **Tier 2**: Edge cases or synthetic data pending verification.
