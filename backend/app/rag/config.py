import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAW_DATA_DIR = os.path.join(PROJECT_ROOT, "backend/data/law_data")

# Law Files (Relative to LAW_DATA_DIR)
LAW_FILES = [
    "raw_law_data/mother_laws/labor_standards_act.json",
    "raw_law_data/subsidiary_laws/enforcement_rules.json",
    "raw_law_data/subsidiary_laws/labor_leave_rule.json",
]

# RAG Settings
OPENAI_MODEL_NAME = "gpt-4o"
# Embedding model configuration is now handled by EmbeddingStrategy (see core/embedding/)
# - v0.0.1, v0.0.2, v0.0.3: OpenAI text-embedding-3-small
# - v0.0.4: BAAI/bge-m3 (HuggingFace local)
OPENAI_TEMPERATURE = 0
CHUNK_SIZE = 1024
RETRIEVER_TOP_K = 5

# RAG Versions
# 0.0.1: Naive (Atomic) Strategy
# 0.0.2: Parent-Child Strategy
RAG_VERSIONS = {
    "0.0.1": "NAIVE",
    "0.0.2": "PARENT_CHILD_FINE",
    "0.0.3": "PARENT_CHILD_COARSE",
    "0.0.4": "BGE_M3_EMBEDDING",
}
LATEST_RAG_VERSION = "0.0.4"

# Vector Store Settings
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# Qdrant Collection Names
COLLECTION_NAME_NAIVE = "naive"
COLLECTION_NAME_PC_FINE = "parent-child-fine"
COLLECTION_NAME_PC_COARSE = "parent-child-coarse"
COLLECTION_NAME_PC_BGE_M3 = "parent-child-bge-m3"
