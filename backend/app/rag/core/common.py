import logging
from llama_index.core import Settings

from backend.app.rag.config import CHUNK_SIZE

logger = logging.getLogger(__name__)


def setup_common_settings(version: str):
    """
    Configures the global LlamaIndex Settings based on the RAG version.

    Uses the EmbeddingStrategy factory to select the correct embedding model:
    - v0.0.x: OpenAI text-embedding-3-small
    - v0.1.x+: BAAI/bge-m3 (HuggingFace local)

    Should be called before any index construction or retrieval.
    """
    from backend.app.rag.factory import get_embedding_strategy  # lazy to avoid circular

    embedding_strategy = get_embedding_strategy(version)
    Settings.embed_model = embedding_strategy.create_embedding()
    Settings.chunk_size = CHUNK_SIZE
