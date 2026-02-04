"""Version-related utility functions for RAG strategy derivation."""

from enum import Enum
from backend.app.rag.types import RagVersion


class ChunkingStrategy(Enum):
    """Chunking strategy enumeration."""

    NAIVE = "naive"
    PARENT_CHILD_FINE = "parent_child_fine"
    PARENT_CHILD_COARSE = "parent_child_coarse"


class EmbeddingModel(Enum):
    """Embedding model enumeration."""

    OPENAI_TEXT_3_SMALL = "openai_text_3_small"
    BAAI_BGE_M3 = "baai_bge_m3"


# Chunking strategy mapping by patch version
_CHUNKING_BY_PATCH = {
    "1": ChunkingStrategy.NAIVE,
    "2": ChunkingStrategy.PARENT_CHILD_FINE,
    "3": ChunkingStrategy.PARENT_CHILD_COARSE,
}


def get_chunking_strategy(version: RagVersion) -> ChunkingStrategy:
    """Derive chunking strategy from version patch number.

    Args:
        version: RAG version enum member

    Returns:
        ChunkingStrategy enum member

    Raises:
        ValueError: If patch version is not recognized
    """
    patch = version.value.split(".")[-1]
    if patch not in _CHUNKING_BY_PATCH:
        raise ValueError(f"Unknown chunking pattern for version {version}")
    return _CHUNKING_BY_PATCH[patch]


def get_embedding_model(version: RagVersion) -> EmbeddingModel:
    """Derive embedding model based on version.

    Rules:
    - v0.0.x: OpenAI text-embedding-3-small
    - v0.1.x and beyond: BAAI/bge-m3

    Args:
        version: RAG version enum member

    Returns:
        EmbeddingModel enum member

    Raises:
        ValueError: If version format is invalid
    """
    parts = version.value.split(".")
    if len(parts) < 2:
        raise ValueError(f"Invalid version format: {version}")

    major = parts[0]
    minor = parts[1]

    if major == "0":
        if minor == "0":
            return EmbeddingModel.OPENAI_TEXT_3_SMALL
        else:
            return EmbeddingModel.BAAI_BGE_M3
    else:
        # Future versions (1.x and beyond) use BAAI/bge-m3
        return EmbeddingModel.BAAI_BGE_M3


def get_strategy_display_name(version: RagVersion) -> str:
    """Generate strategy display name for reporting and logging.

    Args:
        version: RAG version enum member

    Returns:
        Strategy name string, e.g., "PARENT_CHILD_FINE_BAAI_BGE_M3"

    Raises:
        ValueError: If version derivation fails
    """
    chunking = get_chunking_strategy(version)
    embedding = get_embedding_model(version)

    chunking_name = chunking.name
    embedding_name = embedding.name

    return f"{chunking_name}_{embedding_name}"


def get_intermediate_filename(version: RagVersion) -> str:
    """Get intermediate file name for persisted chunking results.

    Args:
        version: RAG version enum member

    Returns:
        Filename string, either "intermediate_nodes_fine.json" or "intermediate_nodes_coarse.json"

    Raises:
        ValueError: If version doesn't support persisted loading (Naive strategy)
    """
    strategy = get_chunking_strategy(version)

    match strategy:
        case ChunkingStrategy.PARENT_CHILD_FINE:
            return "intermediate_nodes_fine.json"
        case ChunkingStrategy.PARENT_CHILD_COARSE:
            return "intermediate_nodes_coarse.json"
        case _:
            raise ValueError(
                f"Version {version.value} does not support persisted loading (Naive strategy)"
            )
