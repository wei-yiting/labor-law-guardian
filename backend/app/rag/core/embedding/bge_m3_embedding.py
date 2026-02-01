import logging

from llama_index.core.embeddings import BaseEmbedding

from backend.app.rag.interface import EmbeddingStrategy

logger = logging.getLogger(__name__)

BGE_M3_MODEL = "BAAI/bge-m3"


class BgeM3EmbeddingStrategy(EmbeddingStrategy):
    """
    Embedding strategy using BAAI/bge-m3 (local HuggingFace model).
    Default embedding for all RAG versions except v0.0.x (which use OpenAI).
    """

    def create_embedding(self) -> BaseEmbedding:
        logger.info(f"Loading local embedding model: {BGE_M3_MODEL}")
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # lazy import

        return HuggingFaceEmbedding(model_name=BGE_M3_MODEL)
