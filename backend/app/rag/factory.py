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
from backend.app.rag.core.embedding.openai_text_3_small_embedding import (
    OpenAIEmbeddingStrategy,
)
from backend.app.rag.core.embedding.bge_m3_embedding import BgeM3EmbeddingStrategy


def _validate_version(version: str) -> RagVersion:
    """Validate version string and return the corresponding RagVersion enum."""
    try:
        return RagVersion(version)
    except ValueError:
        raise ValueError(
            f"Unknown RAG version: {version}. Valid versions: {[v.value for v in RagVersion]}"
        )


def get_retriever_strategy(version: str) -> RetrieverStrategy:
    rag_version = _validate_version(version)

    match rag_version:
        case RagVersion.V0_0_1 | RagVersion.V0_1_1:
            return NaiveRetrieverStrategy(version=rag_version)
        case (
            RagVersion.V0_0_2
            | RagVersion.V0_0_3
            | RagVersion.V0_1_2
            | RagVersion.V0_1_3
        ):
            return ParentChildRetrieverStrategy(version=rag_version)
        case _:
            raise ValueError(f"Strategy not implemented for version: {rag_version}")


def get_embedding_strategy(version: str) -> EmbeddingStrategy:
    """
    Factory function to create the appropriate EmbeddingStrategy based on RAG version.

    - v0.0.1, v0.0.2, v0.0.3: OpenAI text-embedding-3-small
    - All others (v0.1.x+): BAAI/bge-m3 (HuggingFace local)
    """
    rag_version = _validate_version(version)

    match rag_version:
        case RagVersion.V0_0_1 | RagVersion.V0_0_2 | RagVersion.V0_0_3:
            return OpenAIEmbeddingStrategy()
        case _:
            return BgeM3EmbeddingStrategy()


def get_ingestion_strategy(version: str) -> IngestionStrategy:
    rag_version = _validate_version(version)

    match rag_version:
        case RagVersion.V0_0_1 | RagVersion.V0_1_1:
            return NaiveIngestionStrategy(version=rag_version)
        case (
            RagVersion.V0_0_2
            | RagVersion.V0_0_3
            | RagVersion.V0_1_2
            | RagVersion.V0_1_3
        ):
            return ParentChildIngestionStrategy(version=rag_version)
        case _:
            raise ValueError(
                f"Ingestion Strategy not implemented for version: {rag_version}"
            )
