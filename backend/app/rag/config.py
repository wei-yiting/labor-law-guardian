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
# Embedding model configuration is handled by EmbeddingStrategy (see core/embedding/)
# - v0.0.x: OpenAI text-embedding-3-small
# - v0.1.x+: BAAI/bge-m3 (HuggingFace local)
OPENAI_TEMPERATURE = 0
CHUNK_SIZE = 1024
RETRIEVER_TOP_K = 5

# RAG Versions
# v0.0.x: OpenAI text-embedding-3-small
# v0.1.x: BAAI/bge-m3 (same ingestion/retrieval strategies as v0.0.x counterparts)
RAG_VERSIONS = {
    "0.0.1": "NAIVE",
    "0.0.2": "PARENT_CHILD_FINE",
    "0.0.3": "PARENT_CHILD_COARSE",
    "0.1.1": "NAIVE",
    "0.1.2": "PARENT_CHILD_FINE",
    "0.1.3": "PARENT_CHILD_COARSE",
}
LATEST_RAG_VERSION = "0.1.3"

# Vector Store Settings
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"

# Qdrant Collection Names
# v0.0.x (OpenAI embedding)
COLLECTION_NAME_NAIVE = "naive"
COLLECTION_NAME_PC_FINE = "parent-child-fine"
COLLECTION_NAME_PC_COARSE = "parent-child-coarse"
# v0.1.x (bge-m3 embedding)
COLLECTION_NAME_NAIVE_BGE_M3 = "naive-bge-m3"
COLLECTION_NAME_PC_FINE_BGE_M3 = "parent-child-fine-bge-m3"
COLLECTION_NAME_PC_COARSE_BGE_M3 = "parent-child-coarse-bge-m3"
