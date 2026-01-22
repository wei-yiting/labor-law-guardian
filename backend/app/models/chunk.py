from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl

class SplitStrategyEnum(str, Enum):
    atomic = "atomic"
    numeric = "numeric"
    contextual = "contextual"
    numeric_contextual = "numeric_contextual"

class Hierarchy(BaseModel):
    article: str
    paragraph: int | None = None
    subparagraph: int | None = None

class ChunkMetadata(BaseModel):
    url: HttpUrl
    split_strategy: SplitStrategyEnum
    is_expanded: bool
    citation_title: str
    hierarchy: Hierarchy
    chapter_no: int | None = None
    chapter_title: str | None = None
    article_no: str  # Added this field as it was used in the test

class LawChunk(BaseModel):
    chunk_id: str
    parent_id: str
    text: str
    metadata: ChunkMetadata
