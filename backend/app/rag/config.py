
import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LAW_DATA_DIR = os.path.join(PROJECT_ROOT, "backend/data/law_data")

# Law Files (Relative to LAW_DATA_DIR)
LAW_FILES = [
    "labor_standards_act.json",
    "subsidiary_laws/enforcement_rules.json",
    "subsidiary_laws/labor_leave_rule.json"
]

# RAG Settings
OPENAI_MODEL_NAME = "gpt-4o"
EMBEDDING_MODEL_NAME = "text-embedding-3-small"
OPENAI_TEMPERATURE = 0
CHUNK_SIZE = 1024
RETRIEVER_TOP_K = 2
