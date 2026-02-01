from typing import List
from llama_index.core.schema import Node
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from backend.app.rag.interface import RetrieverStrategy
from backend.app.rag.config import (
    RETRIEVER_TOP_K,
    QDRANT_HOST,
    QDRANT_PORT,
    COLLECTION_NAME_PC_FINE,
    COLLECTION_NAME_PC_COARSE,
    COLLECTION_NAME_PC_FINE_BGE_M3,
    COLLECTION_NAME_PC_COARSE_BGE_M3,
)
from backend.app.rag.core.retrieval.postprocessors import ArticleDedupPostprocessor
from backend.app.rag.core.retrieval.components import DiversityRetriever
from backend.app.rag.core.common import setup_common_settings
from backend.app.rag.types import RagVersion


class ParentChildRetrieverStrategy(RetrieverStrategy):
    def __init__(self, version: RagVersion):
        self.version = version

        # Setup Shared Settings
        setup_common_settings(version=version)

        # Determine Collection
        match version:
            case RagVersion.V0_0_2:
                collection_name = COLLECTION_NAME_PC_FINE
            case RagVersion.V0_0_3:
                collection_name = COLLECTION_NAME_PC_COARSE
            case RagVersion.V0_1_2:
                collection_name = COLLECTION_NAME_PC_FINE_BGE_M3
            case RagVersion.V0_1_3:
                collection_name = COLLECTION_NAME_PC_COARSE_BGE_M3
            case _:
                raise ValueError(
                    f"Unknown version for ParentChild Retriever: {version}"
                )

        # Connect to Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        # Initialize Vector Store
        vector_store = QdrantVectorStore(
            collection_name=collection_name, client=client, enable_hybrid=False
        )

        self.index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        # Configure Retriever
        oversample_k = max(RETRIEVER_TOP_K * 5, 10)

        vector_retriever = self.index.as_retriever(similarity_top_k=oversample_k)

        dedup_processor = ArticleDedupPostprocessor()

        self.diversity_retriever = DiversityRetriever(
            retriever=vector_retriever, node_postprocessors=[dedup_processor]
        )

    def retrieve(self, query: str) -> List[Node]:
        # 4. Limit to top_k
        nodes = self.diversity_retriever.retrieve(query)
        return nodes[:RETRIEVER_TOP_K]

    def get_retrieved_article_id(self, node: Node) -> str:
        # Priority: Parent ID -> Article ID
        return node.metadata.get("parent_id") or node.metadata.get("article_id")
