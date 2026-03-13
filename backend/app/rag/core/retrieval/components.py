from typing import List
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

class DiversityRetriever(BaseRetriever):
    """
    Custom Retriever wrapper that applies diversity reranking (deduplication)
    AFTER the initial vector retrieval.
    """
    def __init__(
        self, 
        retriever: BaseRetriever, 
        node_postprocessors: List[BaseNodePostprocessor]
    ):
        self._retriever = retriever
        self._postprocessors = node_postprocessors
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        # 1. Initial Retrieval (Oversampled)
        nodes = self._retriever.retrieve(query_bundle)
        
        # 2. Apply Postprocessors
        for processor in self._postprocessors:
            nodes = processor.postprocess_nodes(nodes, query_bundle=query_bundle)
            
        return nodes
