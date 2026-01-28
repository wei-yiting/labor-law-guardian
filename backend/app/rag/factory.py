from backend.app.rag.interface import RetrieverStrategy, IngestionStrategy
from backend.app.rag.types import RagVersion
from backend.app.rag.core.retrieval.naive_retrieval import NaiveRetrieverStrategy
from backend.app.rag.core.retrieval.parent_child_retrieval import (
    ParentChildRetrieverStrategy,
)
from backend.app.rag.core.ingestion.naive_ingestion import NaiveIngestionStrategy
from backend.app.rag.core.ingestion.parent_child_ingestion import (
    ParentChildIngestionStrategy,
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
