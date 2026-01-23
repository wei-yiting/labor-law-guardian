
import os
import argparse
from typing import List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Adjust import to fetch from config
try:
    from backend.app.rag.config import (
        OPENAI_MODEL_NAME, 
        EMBEDDING_MODEL_NAME, 
        OPENAI_TEMPERATURE, 
        CHUNK_SIZE, 
        RETRIEVER_TOP_K
    )
    from backend.app.rag.retriever.law_data_loader import load_law_data
    from backend.app.rag.retriever.postprocessors import ArticleDedupPostprocessor
except ImportError:
    import sys
    # Add project root (4 levels up from backend/app/rag/retriever/engine.py)
    # engine.py is in backend/app/rag/retriever
    # .../backend/app/rag/retriever -> .../backend -> .../
    project_root = Path(__file__).resolve().parents[4]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

    from backend.app.rag.config import (
        OPENAI_MODEL_NAME, 
        EMBEDDING_MODEL_NAME, 
        OPENAI_TEMPERATURE, 
        CHUNK_SIZE, 
        RETRIEVER_TOP_K,
        RAG_VERSIONS,
        LATEST_RAG_VERSION
    )
    from backend.app.rag.ingestion.law_data_loader import load_law_data
    from backend.app.rag.ingestion.parent_child_loader import load_parent_child_data
    from backend.app.rag.retriever.postprocessors import ArticleDedupPostprocessor

from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.postprocessor.types import BaseNodePostprocessor

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

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

def get_index(rag_version: str = LATEST_RAG_VERSION):
    """
    Initializes and returns the VectorStoreIndex.
    Configures Settings with OpenAI models from config.
    """
    
    # Global Settings Configuration
    Settings.llm = OpenAI(model=OPENAI_MODEL_NAME, temperature=OPENAI_TEMPERATURE)
    Settings.embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL_NAME)
    Settings.chunk_size = CHUNK_SIZE
    
    strategy = RAG_VERSIONS.get(rag_version)
    if not strategy:
        raise ValueError(f"Invalid RAG version: {rag_version}. Available: {list(RAG_VERSIONS.keys())}")
    
    print(f"Building Index for Version: {rag_version} (Strategy: {strategy})")
    
    # Init DocStore (Not needed for Manual Lookup)
    # docstore = SimpleDocumentStore() 
    # storage_context = StorageContext.from_defaults(docstore=docstore)
    
    # Load Documents
    if "PARENT_CHILD" in strategy:
        leaf_nodes, _ = load_parent_child_data(rag_version=rag_version)
        
        # Index Leaf Nodes ONLY
        documents = leaf_nodes 
    else: # NAIVE
        documents = load_law_data()
        
    # Build Index
    index = VectorStoreIndex(
        documents
    )
    
    return index

def get_retriever(similarity_top_k: int = RETRIEVER_TOP_K, rag_version: str = LATEST_RAG_VERSION):
    """
    Returns a retriever configured with top_k defined in config or override.
    Wraps the standard retriever with DiversityRetriever to apply deduplication.
    """
    index = get_index(rag_version=rag_version)
    
    # OVERSAMPLING: Set internal retriever k to 5x the target top_k (or at least 10)
    # This ensures we have enough candidates after filtering duplicates.
    oversample_k = max(similarity_top_k * 5, 10)
    
    print(f"Configuring Diversity Retriever: Target Top-K={similarity_top_k}, Oversample Top-K={oversample_k}")
    
    # Standard Vector Retriever
    vector_retriever = index.as_retriever(similarity_top_k=oversample_k)
    
    # Postprocessor
    dedup_processor = ArticleDedupPostprocessor()
    
    # Wrap in DiversityRetriever
    diversity_retriever = DiversityRetriever(
        retriever=vector_retriever,
        node_postprocessors=[dedup_processor]
    )
    
    # NOTE: The DiversityRetriever will return UP TO oversample_k items.
    # If we want to strictly trim back to similarity_top_k, we can add a slicer or do it here.
    # However, usually having slightly more high-quality unique items is OK. 
    # But strictly speaking, "top_k" usually implies a limit.
    # Let's enforce the limit via a simple slice in the post-processing or a limit processor.
    # For now, let's keep it simple: the dedup might reduce list size significantly.
    # If we want exactly top_k, we should slice at the end.
    
    class LimitPostprocessor(BaseNodePostprocessor):
        def _postprocess_nodes(self, nodes, query_bundle):
            return nodes[:similarity_top_k]
            
    diversity_retriever = DiversityRetriever(
        retriever=vector_retriever,
        node_postprocessors=[dedup_processor, LimitPostprocessor()]
    )

    return diversity_retriever

if __name__ == "__main__":
    # CLI Argument Parsing
    parser = argparse.ArgumentParser(description="Test the RAG Retriever Engine.")
    parser.add_argument(
        "--query", 
        type=str, 
        default="勞工退休金幾歲可以領？", 
        help="Query string to retrieve documents for."
    )
    args = parser.parse_args()

    # Test the engine
    try:
        retriever = get_retriever()
        nodes = retriever.retrieve(args.query)
        print(f"\nRetrieval Result for: '{args.query}'")
        for node in nodes:
            print("-" * 20)
            print(f"Score: {node.score}")
            print(f"Node ID: {node.id_}")
            print(f"Metadata: {node.metadata}")
            print(f"Text Snippet: {node.get_text()[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
