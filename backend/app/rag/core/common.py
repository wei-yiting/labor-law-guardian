from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from backend.app.rag.config import (
    OPENAI_MODEL_NAME, EMBEDDING_MODEL_NAME, 
    OPENAI_TEMPERATURE, CHUNK_SIZE
)

def setup_common_settings():
    """
    Configures the global LlamaIndex Settings.
    Should be called before any index construction or retrieval.
    """
    Settings.llm = OpenAI(model=OPENAI_MODEL_NAME, temperature=OPENAI_TEMPERATURE)
    Settings.embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL_NAME)
    Settings.chunk_size = CHUNK_SIZE
