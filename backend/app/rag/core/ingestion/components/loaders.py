import json
import logging
from pathlib import Path
from typing import List
from llama_index.core.schema import TextNode
from backend.app.rag.config import LAW_DATA_DIR
from backend.app.rag.types import RagVersion
from backend.app.rag.version_utils import get_intermediate_filename

logger = logging.getLogger(__name__)


def load_persisted_nodes(version: str) -> List[TextNode]:
    """
    Load persisted intermediate nodes (Law Chunks) for a specific RAG version.

    This ensures both Ingestion (to persistence) and Retrieval (from persistence)
    use the exact same data source, adhering to the Single Source of Truth principle.

    Args:
        version (str): The RAG version (e.g., "0.0.2", "0.1.2").

    Returns:
        List[TextNode]: A list of LlamaIndex TextNodes reconstructed from the persisted JSON.

    Raises:
        ValueError: If version is unknown or doesn't support persisted loading
        FileNotFoundError: If persisted data file is not found
    """
    # Validate and convert to RagVersion enum
    try:
        rag_version = RagVersion(version)
    except ValueError:
        raise ValueError(
            f"Unknown RAG version: {version}. Valid versions: {[v.value for v in RagVersion]}"
        )

    # Get filename based on version
    try:
        filename = get_intermediate_filename(rag_version)
    except ValueError as e:
        raise ValueError(str(e))

    file_path = Path(LAW_DATA_DIR) / "parent_child_index" / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Persisted data not found at {file_path}. Please run Ingestion first."
        )

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = []
    for item in data:
        # Reconstruct the TextNode
        # Note: The Qdrant Ingestor or Retriever might perform additional
        # payload transformations, but this loader returns the raw "LlamaIndex Node"
        # representation of the persisted chunk.

        metadata = item.get("metadata", {})

        # Flattened Metadata mapping if needed, but here we load what was saved.
        # Assuming saved format matches LawChunk model dump.

        node = TextNode(
            text=item.get("text"),
            id_=item.get("chunk_id"),
            metadata=metadata,
        )

        # Manually ensure crucial IDs are in metadata if missing (redundancy check)
        if "chunk_id" not in node.metadata:
            node.metadata["chunk_id"] = item.get("chunk_id")
        if "parent_id" not in node.metadata:
            node.metadata["parent_id"] = item.get("parent_id")

        nodes.append(node)

    logger.info(f"Loaded {len(nodes)} persisted nodes from {filename}")
    return nodes
