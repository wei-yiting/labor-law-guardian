import json
import logging
import uuid
from pathlib import Path
from typing import List, Any
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.schema import Document
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.app.rag.core.common import setup_common_settings
from backend.app.rag.interface import IngestionStrategy
from backend.app.rag.types import RagVersion
from backend.app.rag.core.ingestion.components.chunker import LawArticleChunker
from backend.app.rag.core.ingestion.components.loaders import load_persisted_nodes
from backend.app.rag.config import (
    LAW_DATA_DIR,
    LAW_FILES,
    RAG_VERSIONS,
    COLLECTION_NAME_PC_FINE,
    COLLECTION_NAME_PC_COARSE,
    COLLECTION_NAME_PC_FINE_BGE_M3,
    COLLECTION_NAME_PC_COARSE_BGE_M3,
    QDRANT_HOST,
    QDRANT_PORT,
)

logger = logging.getLogger(__name__)


class ParentChildIngestionStrategy(IngestionStrategy):
    """
    Ingestion Strategy for Parent-Child RAG.
    Supports v0.0.2/v0.0.3 (OpenAI embedding) and v0.1.2/v0.1.3 (bge-m3 embedding).
    1. Chunks raw data using LawArticleChunker.
    2. Persists chunks to Intermediate JSON.
    3. Ingests chunks into Qdrant.
    """

    def __init__(self, version: RagVersion):
        self.version = version
        self.strategy_name = RAG_VERSIONS.get(version)
        if not self.strategy_name:
            raise ValueError(
                f"Invalid version for ParentChildIngestionStrategy: {version}"
            )

    def run(self, documents: List[Document] = None, **kwargs) -> Any:
        logger.info(
            f"Running Parent-Child Ingestion Strategy ({self.version}: {self.strategy_name})"
        )

        chunker = LawArticleChunker(strategy=self.strategy_name)

        # Process law files defined in config
        full_paths = [str(Path(LAW_DATA_DIR) / f) for f in LAW_FILES]
        all_chunks = chunker.process_files(full_paths)

        if not all_chunks:
            logger.warning("No chunks generated")
            return []

        self._persist_chunks(all_chunks)

        # Reload persisted nodes to ensure Single Source of Truth
        nodes = load_persisted_nodes(self.version)

        if kwargs.get("dry_run", False):
            logger.info(
                "Dry run mode: Skipping Qdrant ingestion (chunks persisted locally)"
            )
            return nodes

        # Convert semantic IDs to UUIDs for Qdrant compatibility
        # Qdrant only accepts UUID or integer point IDs, but our chunk IDs are
        # semantic strings (e.g., 'LSA-24_P1'). We generate deterministic UUIDs
        # and preserve the original semantic ID in metadata for traceability.
        logger.debug("Converting semantic node IDs to UUIDs for Qdrant")
        for node in nodes:
            original_id = node.node_id

            if "chunk_id" not in node.metadata:
                node.metadata["chunk_id"] = original_id

            # Use DNS namespace for deterministic UUID generation
            new_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, original_id))
            node.id_ = new_id

        # Determine target Qdrant collection based on version
        match self.version:
            case RagVersion.V0_0_2:
                collection = COLLECTION_NAME_PC_FINE
            case RagVersion.V0_0_3:
                collection = COLLECTION_NAME_PC_COARSE
            case RagVersion.V0_1_2:
                collection = COLLECTION_NAME_PC_FINE_BGE_M3
            case RagVersion.V0_1_3:
                collection = COLLECTION_NAME_PC_COARSE_BGE_M3
            case _:
                logger.warning(
                    f"Unknown version {self.version} for Qdrant ingestion, skipping"
                )
                return nodes

        # Setup global embedding settings before ingestion
        setup_common_settings(version=self.version)

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Dense-only vector store (hybrid search disabled per requirements)
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection,
            enable_hybrid=False,
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Create index (uses Settings.embed_model configured above)
        _ = VectorStoreIndex(  # Side effect only: persists embeddings to Qdrant
            nodes=nodes, storage_context=storage_context
        )

        logger.info(
            f"Successfully ingested {len(nodes)} nodes into collection '{collection}'"
        )
        return nodes

    def _persist_chunks(self, chunks: List[Any]):
        """
        Persist chunks to the appropriate Intermediate JSON file.
        """
        output_dir = Path(LAW_DATA_DIR) / "parent_child_index"
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.strategy_name == "PARENT_CHILD_COARSE":
            filename = "intermediate_nodes_coarse.json"
        else:
            filename = "intermediate_nodes_fine.json"

        file_path = output_dir / filename

        # Convert Pydantic models to list of dicts
        chunks_data = [chunk.model_dump(mode="json") for chunk in chunks]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Persisted {len(chunks)} chunks to {file_path}")
