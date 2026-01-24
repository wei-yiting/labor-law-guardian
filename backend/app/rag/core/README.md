# RAG Core Components

This directory (`backend/app/rag/core`) contains the independent, reusable library logic for the RAG pipeline.

## Submodules

### `retrieval/`

Contains the concrete implementations of `RetrieverStrategy`.

- **`naive.py`**:
  - Implements `NaiveRetrieverStrategy`.
  - Logic: Standard Vector Search using `VectorStoreIndex`.
  - Key Feature: Simple baseline, no de-duplication.
- **`parent_child.py`**:
  - Implements `ParentChildRetrieverStrategy`.
  - Logic: Retrieves granular "Child" chunks (leafs) but maps them back to "Parent" Articles.
  - Key Feature: Uses `DiversityRetriever` (in `components.py`) to deduplicate results, ensuring diverse parent articles in the context window.
- **`components.py`**:
  - Shared building blocks.
  - `DiversityRetriever`: A wrapper that performs Oversampling -> Postprocessing (Dedup) -> Top-K Limiting.

### `evaluation/`

Contains logic for measuring RAG performance.

- **`evaluator.py`**:
  - `RetrieverEvaluator`: The core class that orchestrates retrieval and metric calculation.
  - **Polymorphism**: It calls `strategy.get_retrieved_article_id(node)` to correctly handle different ID structures (Article ID vs Parent ID) without `if-else` hacks.
- **`reporting.py`**:
  - Helper functions to write JSON logs (`backend/experiments/`) and Text Reports (`backend/app/rag/evals/reports/`).

### `common.py`

- `setup_common_settings()`: Centralizes LlamaIndex global configuration (LLM, Embed Model, Chunk Size) to ensure consistency across all strategies.
