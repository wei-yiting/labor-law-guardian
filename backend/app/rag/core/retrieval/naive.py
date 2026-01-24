from typing import List
from llama_index.core.schema import Node
from llama_index.core import VectorStoreIndex

from backend.app.rag.interface import RetrieverStrategy
from backend.app.rag.config import RETRIEVER_TOP_K
from backend.app.rag.ingestion.law_data_loader import load_law_data
from backend.app.rag.core.common import setup_common_settings

class NaiveRetrieverStrategy(RetrieverStrategy):
    def __init__(self):
        # 1. Setup Shared Settings
        setup_common_settings()
        
        # 2. Load Data & Build Index ONCE
        documents = load_law_data()
        self.index = VectorStoreIndex(documents)
        
        # 3. Configure Retriever
        # Naive strategy does not use deduplication, so we can use standard top_k
        self.retriever = self.index.as_retriever(similarity_top_k=RETRIEVER_TOP_K)

    def retrieve(self, query: str) -> List[Node]:
        nodes = self.retriever.retrieve(query)
        return nodes

    def get_retrieved_article_id(self, node: Node) -> str:
        return node.metadata.get("article_id")

