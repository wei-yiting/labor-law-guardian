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

### `embedding/`

Contains the concrete implementations of `EmbeddingStrategy`.

- **`openai_text_3_small_embedding.py`**:
  - Implements `OpenAIEmbeddingStrategy`.
  - Uses `text-embedding-3-small` (OpenAI API).
  - Used by RAG versions 0.0.1, 0.0.2, 0.0.3.
- **`baai_bge_m3_embedding.py`**:
  - Implements `BgeM3EmbeddingStrategy`.
  - Uses `BAAI/bge-m3` (local HuggingFace model).
  - Default for all versions except v0.0.x (v0.1.1, v0.1.2, v0.1.3, etc.).

### `common.py`

- `setup_common_settings(version)`: Centralizes LlamaIndex global configuration (Embed Model, Chunk Size) to ensure consistency across all strategies. Uses `get_embedding_strategy(version)` to select the correct embedding model based on the RAG version.
