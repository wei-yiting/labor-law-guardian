import logging

from llama_index.core.embeddings import BaseEmbedding

from backend.app.rag.interface import EmbeddingStrategy

logger = logging.getLogger(__name__)

OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingStrategy(EmbeddingStrategy):
    """
    Embedding strategy using OpenAI text-embedding-3-small.
    Used by RAG versions 0.0.1, 0.0.2, 0.0.3.
    """

    def create_embedding(self) -> BaseEmbedding:
        logger.info(f"Loading OpenAI embedding model: {OPENAI_EMBEDDING_MODEL}")
        from llama_index.embeddings.openai import OpenAIEmbedding  # lazy import

        return OpenAIEmbedding(model=OPENAI_EMBEDDING_MODEL)
