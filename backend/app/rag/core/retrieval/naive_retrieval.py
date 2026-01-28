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
    COLLECTION_NAME_NAIVE
)
from backend.app.rag.core.common import setup_common_settings

class NaiveRetrieverStrategy(RetrieverStrategy):
    def __init__(self):
        # 1. Setup Shared Settings
        setup_common_settings()
        
        # 2. Connect to Qdrant
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # 3. Initialize Vector Store & Index
        vector_store = QdrantVectorStore(
            collection_name=COLLECTION_NAME_NAIVE,
            client=client
        )
        
        self.index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        
        # 4. Configure Retriever
        self.retriever = self.index.as_retriever(similarity_top_k=RETRIEVER_TOP_K)

    def retrieve(self, query: str) -> List[Node]:
        nodes = self.retriever.retrieve(query)
        return nodes

    def get_retrieved_article_id(self, node: Node) -> str:
        return node.metadata.get("article_id")
