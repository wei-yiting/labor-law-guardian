# Retrieval Layer

## Responsibilities

Contains `RetrieverStrategy` implementations.
These classes orchestrate the retrieval pipeline: `Query -> Vector Search -> Post-Processing -> Nodes`.

The Retrieval Process generally follows these steps:

1.  **Query Input**: Receive user query.
2.  **Vector Search**: Search Qdrant for Top-K semantic matches.
3.  **Oversampling**: Fetch more candidates than needed (e.g., 5x Top-K) to allow for filtering.
4.  **Post-Processing**: Apply diversity filters, deduplication, or reranking.
5.  **Final Selection**: Return the final list of Nodes to the engine.

## Map

- **`naive_retrieval.py`**: (v0.0.1) Simple Top-K vector search.
- **`parent_child_retrieval.py`**: (v0.0.2 / v0.0.3) Complex pipeline:
  - Uses `DiversityRetriever` (custom component).
  - Applies Oversampling.
  - Applies `ArticleDedupPostprocessor` to diverse results.

## Extension Guidelines

To add a new retriever:

1.  Create class inheriting from `RetrieverStrategy`.
2.  Initialize your `VectorStoreIndex` (usually connecting to an existing Qdrant collection).
3.  Implement `retrieve(self, query) -> List[Node]`.
