from abc import ABC, abstractmethod
from typing import List, Any
from llama_index.core.schema import Node, Document


class IngestionStrategy(ABC):
    """
    Abstract Base Class for Ingestion Strategies.
    Responsible for processing raw documents into chunks/nodes and indexing them.
    """
    @abstractmethod
    def run(self, documents: List[Document], **kwargs) -> Any:
        pass

class RetrieverStrategy(ABC):
    """
    Abstract Base Class for Retrieval Strategies.
    Responsible for retrieving relevant nodes for a given query and handling
    evaluation ID logic.
    """
    @abstractmethod
    def retrieve(self, query: str) -> List[Node]:
        pass

    @abstractmethod
    def get_retrieved_article_id(self, node: Node) -> str:
        """
        Returns the key used for evaluation comparison against Ground Truth.
        
        For Naive RAG, this is the 'article_id' of the chunk.
        For Parent-Child RAG, this is the 'parent_id' (Article ID) of the chunk.
        """
        pass
