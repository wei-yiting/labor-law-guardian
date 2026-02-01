from backend.app.rag.interface import RetrieverStrategy, IngestionStrategy, EmbeddingStrategy
from backend.app.rag.types import RagVersion
from backend.app.rag.core.retrieval.naive_retrieval import NaiveRetrieverStrategy
from backend.app.rag.core.retrieval.parent_child_retrieval import (
    ParentChildRetrieverStrategy,
)
from backend.app.rag.core.ingestion.naive_ingestion import NaiveIngestionStrategy
from backend.app.rag.core.ingestion.parent_child_ingestion import (
    ParentChildIngestionStrategy,
)
from backend.app.rag.core.embedding.openai_embedding import OpenAIEmbeddingStrategy
from backend.app.rag.core.embedding.huggingface_embedding import (
    HuggingFaceEmbeddingStrategy,
)


def get_retriever_strategy(version: str) -> RetrieverStrategy:
    # Validate version string by trying to construct Enum
    try:
        rag_version = RagVersion(version)
    except ValueError:
        raise ValueError(
            f"Unknown RAG version: {version}. Valid versions: {[v.value for v in RagVersion]}"
        )

    match rag_version:
        case RagVersion.V0_0_1:
            return NaiveRetrieverStrategy()
        case RagVersion.V0_0_2 | RagVersion.V0_0_3 | RagVersion.V0_0_4:
            return ParentChildRetrieverStrategy(version=version)
        case _:
            # Should be unreachable if Enum covers all cases, but good practice
            raise ValueError(f"Strategy not implemented for version: {rag_version}")


def get_embedding_strategy(version: str) -> EmbeddingStrategy:
    """
    Factory function to create the appropriate EmbeddingStrategy based on RAG version.

    - v0.0.1, v0.0.2, v0.0.3: OpenAI text-embedding-3-small
    - v0.0.4: BAAI/bge-m3 (HuggingFace local)
    """
    try:
        rag_version = RagVersion(version)
    except ValueError:
        raise ValueError(
            f"Unknown RAG version: {version}. Valid versions: {[v.value for v in RagVersion]}"
        )

    match rag_version:
        case RagVersion.V0_0_1 | RagVersion.V0_0_2 | RagVersion.V0_0_3:
            return OpenAIEmbeddingStrategy()
        case RagVersion.V0_0_4:
            return HuggingFaceEmbeddingStrategy()
        case _:
            raise ValueError(
                f"Embedding Strategy not implemented for version: {rag_version}"
            )


def get_ingestion_strategy(version: str) -> IngestionStrategy:
    # Validate version
    try:
        rag_version = RagVersion(version)
    except ValueError:
        raise ValueError(
            f"Unknown RAG version: {version}. Valid versions: {[v.value for v in RagVersion]}"
        )

    match rag_version:
        case RagVersion.V0_0_1:
            return NaiveIngestionStrategy()
        case RagVersion.V0_0_2 | RagVersion.V0_0_3 | RagVersion.V0_0_4:
            return ParentChildIngestionStrategy(version=version)
        case _:
            raise ValueError(
                f"Ingestion Strategy not implemented for version: {rag_version}"
            )
