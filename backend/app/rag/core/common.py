import logging
from llama_index.core import Settings

from backend.app.rag.config import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_PROVIDER,
    CHUNK_SIZE,
)

logger = logging.getLogger(__name__)


def setup_common_settings():
    """
    Configures the global LlamaIndex Settings.
    Should be called before any index construction or retrieval.
    """
    # Lazy imports to avoid heavy loading at module level
    if EMBEDDING_PROVIDER == "huggingface":
        logger.info(f"Loading local embedding model: {EMBEDDING_MODEL_NAME}")
        from llama_index.embeddings.huggingface import (
            HuggingFaceEmbedding,
        )  # lazy import

        Settings.embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL_NAME)
    elif EMBEDDING_PROVIDER == "openai":
        logger.info(f"Loading OpenAI embedding model: {EMBEDDING_MODEL_NAME}")
        from llama_index.embeddings.openai import OpenAIEmbedding  # lazy import

        Settings.embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL_NAME)
    else:
        raise ValueError(f"Unknown EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")

    Settings.chunk_size = CHUNK_SIZE
