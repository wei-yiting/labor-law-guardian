import logging
from typing import List, Any
from llama_index.core.schema import Document
from qdrant_client import QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from llama_index.core import VectorStoreIndex

from backend.app.rag.core.common import setup_common_settings
from backend.app.rag.interface import IngestionStrategy
from backend.app.rag.core.ingestion.components.raw_loader import load_raw_law_documents
from backend.app.rag.config import COLLECTION_NAME_NAIVE, QDRANT_HOST, QDRANT_PORT

logger = logging.getLogger(__name__)


class NaiveIngestionStrategy(IngestionStrategy):
    """
    Ingestion Strategy for Naive RAG (v0.0.1).
    Loads raw documents and ingests them into Qdrant (Dense only).
    """

    def run(self, documents: List[Document] = None, **kwargs) -> Any:
        logger.info("Running Naive Ingestion Strategy")

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
        setup_common_settings(version="0.0.1")

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Dense-only vector store (hybrid search disabled per requirements)
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=COLLECTION_NAME_NAIVE,
            enable_hybrid=False,
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Create index (handles embedding generation and ingestion)
        # Uses Settings.embed_model configured in setup_common_settings()
        _ = VectorStoreIndex(nodes=documents, storage_context=storage_context)

        logger.info(
            f"Successfully ingested {len(documents)} documents into collection '{COLLECTION_NAME_NAIVE}'"
        )
        return documents
