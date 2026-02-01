# Embedding Strategies

This directory contains concrete implementations of the `EmbeddingStrategy` interface, which provides a consistent way to create embedding model instances based on RAG version.

## Files

| File | Class | Model | Used By |
| :--- | :---- | :---- | :------ |
| `openai_embedding.py` | `OpenAIEmbeddingStrategy` | `text-embedding-3-small` | v0.0.1, v0.0.2, v0.0.3 |
| `huggingface_embedding.py` | `HuggingFaceEmbeddingStrategy` | `BAAI/bge-m3` | v0.0.4 |

## Architecture

The `EmbeddingStrategy` interface (`backend/app/rag/interface.py`) defines a single method:

```python
class EmbeddingStrategy(ABC):
    @abstractmethod
    def create_embedding(self) -> BaseEmbedding:
        """Return a configured LlamaIndex embedding model instance."""
        pass
```

The factory function `get_embedding_strategy(version)` in `backend/app/rag/factory.py` selects the correct strategy based on the RAG version string.

## Extension Guide

To add a new embedding model:

1. Create a new file in this directory (e.g., `cohere_embedding.py`).
2. Implement the `EmbeddingStrategy` interface.
3. Register the new strategy in `backend/app/rag/factory.py::get_embedding_strategy()`.
