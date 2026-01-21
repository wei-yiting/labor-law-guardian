
import os
import argparse
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
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[4]))
    from backend.app.rag.config import (
        OPENAI_MODEL_NAME, 
        EMBEDDING_MODEL_NAME, 
        OPENAI_TEMPERATURE, 
        CHUNK_SIZE, 
        RETRIEVER_TOP_K
    )
    from backend.app.rag.retriever.law_data_loader import load_law_data

from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

def get_index():
    """
    Initializes and returns the VectorStoreIndex.
    Configures Settings with OpenAI models from config.
    """
    
    # Global Settings Configuration
    Settings.llm = OpenAI(model=OPENAI_MODEL_NAME, temperature=OPENAI_TEMPERATURE)
    Settings.embed_model = OpenAIEmbedding(model=EMBEDDING_MODEL_NAME)
    Settings.chunk_size = CHUNK_SIZE
    
    # Load Documents
    documents = load_law_data()
    # print(f"Indexing {len(documents)} documents...")
    
    # Build Index
    index = VectorStoreIndex.from_documents(documents)
    # print("Index built successfully.")
    
    return index

def get_retriever(similarity_top_k: int = RETRIEVER_TOP_K):
    """
    Returns a retriever configured with top_k defined in config or override.
    """
    index = get_index()
    return index.as_retriever(similarity_top_k=similarity_top_k)

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
