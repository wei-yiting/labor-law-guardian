
import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAW_DATA_DIR = os.path.join(PROJECT_ROOT, "backend/data/law_data")

# Law Files (Relative to LAW_DATA_DIR)
LAW_FILES = [
    "raw_law_data/mother_laws/labor_standards_act.json",
    "raw_law_data/subsidiary_laws/enforcement_rules.json",
    "raw_law_data/subsidiary_laws/labor_leave_rule.json"
]

# RAG Settings
OPENAI_MODEL_NAME = "gpt-4o"
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
OPENAI_TEMPERATURE = 0
CHUNK_SIZE = 1024
RETRIEVER_TOP_K = 3

# RAG Versions
# 0.0.1: Naive (Atomic) Strategy
# 0.0.2: Parent-Child Strategy
RAG_VERSIONS = {
    "0.0.1": "NAIVE",
    "0.0.2": "PARENT_CHILD_FINE",
    "0.0.3": "PARENT_CHILD_COARSE"
}
LATEST_RAG_VERSION = "0.0.3"
