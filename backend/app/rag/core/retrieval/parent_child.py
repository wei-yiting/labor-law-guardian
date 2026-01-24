from typing import List
from llama_index.core.schema import Node
from llama_index.core import VectorStoreIndex

from backend.app.rag.interface import RetrieverStrategy
from backend.app.rag.config import RETRIEVER_TOP_K
from backend.app.rag.ingestion.parent_child_loader import load_parent_child_data
from backend.app.rag.core.retrieval.postprocessors import ArticleDedupPostprocessor
from backend.app.rag.core.retrieval.components import DiversityRetriever
from backend.app.rag.core.common import setup_common_settings

class ParentChildRetrieverStrategy(RetrieverStrategy):
    def __init__(self, version: str):
        self.version = version
        
        # 1. Setup Shared Settings
        setup_common_settings()
        
        # 2. Load Leaf Nodes & Build Index ONCE
        leaf_nodes, _ = load_parent_child_data(rag_version=self.version)
        self.index = VectorStoreIndex(leaf_nodes)
        
        # 3. Configure Retriever ONCE (optional, or per query if dynamic k)
        oversample_k = max(RETRIEVER_TOP_K * 5, 10)
        vector_retriever = self.index.as_retriever(similarity_top_k=oversample_k)
        
        dedup_processor = ArticleDedupPostprocessor()
        
        self.diversity_retriever = DiversityRetriever(
            retriever=vector_retriever,
            node_postprocessors=[dedup_processor]
        )

    def retrieve(self, query: str) -> List[Node]:
        # 4. Limit to top_k
        nodes = self.diversity_retriever.retrieve(query)
        return nodes[:RETRIEVER_TOP_K]

    def get_retrieved_article_id(self, node: Node) -> str:
        # Priority: Parent ID -> Article ID
        return node.metadata.get("parent_id") or node.metadata.get("article_id")

