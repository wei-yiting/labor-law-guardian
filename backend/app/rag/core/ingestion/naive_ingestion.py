import logging
from typing import List, Any
from llama_index.core.schema import Document
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex

from backend.app.rag.core.common import setup_common_settings
from backend.app.rag.interface import IngestionStrategy
from backend.app.rag.types import RagVersion
from backend.app.rag.core.ingestion.components.raw_loader import load_raw_law_documents
from backend.app.rag.config import (
    COLLECTION_NAME_NAIVE,
    COLLECTION_NAME_NAIVE_BGE_M3,
    QDRANT_HOST,
    QDRANT_PORT,
)

logger = logging.getLogger(__name__)


class NaiveIngestionStrategy(IngestionStrategy):
    """
    Ingestion Strategy for Naive RAG (v0.0.1 / v0.1.1).
    Loads raw documents and ingests them into Qdrant (Dense only).
    """

    def __init__(self, version: RagVersion = RagVersion.V0_0_1):
        self.version = version

    def run(self, documents: List[Document] = None, **kwargs) -> Any:
        logger.info(f"Running Naive Ingestion Strategy ({self.version})")

        # Load documents if not provided (allows testing with specific docs)
        if not documents:
            documents = load_raw_law_documents()

        if not documents:
            logger.warning("No documents to ingest")
            return []

        if kwargs.get("dry_run", False):
            logger.info("Dry run mode: Skipping Qdrant ingestion")
            return documents

        # Setup global embedding settings before ingestion
        setup_common_settings(version=self.version)

        # Determine collection
        if self.version == RagVersion.V0_1_1:
            collection_name = COLLECTION_NAME_NAIVE_BGE_M3
        else:
            collection_name = COLLECTION_NAME_NAIVE

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Dense-only vector store (hybrid search disabled per requirements)
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            enable_hybrid=False,
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Create index (handles embedding generation and ingestion)
        # Uses Settings.embed_model configured in setup_common_settings()
        _ = VectorStoreIndex(nodes=documents, storage_context=storage_context)

        logger.info(
            f"Successfully ingested {len(documents)} documents into collection '{collection_name}'"
        )
        return documents
