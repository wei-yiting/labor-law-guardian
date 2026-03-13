# Ingestion Components

## Responsibilities

Reusable logic used by multiple Ingestion Strategies.
These components should remain stateless and focused on data transformation.

## Map

- **`chunker.py`**: Core domain logic for splitting Law Articles. Supports:
  - `PARENT_CHILD_FINE` (v0.0.2): Recursive split (Article -> Paragraph -> Subparagraph).
  - `PARENT_CHILD_COARSE` (v0.0.3): Numeric Paragraph split only.
- **`loaders.py`**: Utilities for loading _processed_ or _persisted_ nodes (e.g., reading back the intermediate JSON).
- **`raw_loader.py`**: Loads the raw `LawData` JSON files from disk into LlamaIndex Documents.

## Extension Guidelines

- **New Split Logic**: Add a method to `LawArticleChunker` or a new class if logic is vastly different.
- **New Loader**: Add to `loaders.py` only if it's a generic utility.
