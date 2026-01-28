# Ingestion Layer

## Responsibilities

This directory contains concrete `IngestionStrategy` implementations.
Each file corresponds to a specific RAG version's indexing logic.

The Ingestion Process generally follows these steps:

1.  **Load**: Read raw data (from disk or scraper).
2.  **Transform**: Chunk or split the data (using `components/chunker.py`).
3.  **Embed & Index**: Generate embeddings and store them in the Vector Database (Qdrant).
4.  **Persist**: Optionally save intermediate states (e.g., JSON) for reproducibility.

## Map

- **`naive_ingestion.py`**: (v0.0.1) Simple loading of full articles directly into Qdrant. Dense-only.
- **`parent_child_ingestion.py`**: (v0.0.2 / v0.0.3) Advanced strategy:
  1.  Splits articles into smaller chunks (Fine/Coarse).
  2.  Persists chunks to `backend/data/law_data/parent_child_index/` (Intermediate Layer).
  3.  Ingests chunks into Qdrant.

## Extension Guidelines

To add a new strategy (e.g., `hybrid_ingestion.py`):

1.  Create the file `hybrid_ingestion.py`.
2.  Inherit from `IngestionStrategy`.
3.  Implement `run(self, documents, **kwargs)`.
4.  Register it in `backend/app/rag/factory.py`.
