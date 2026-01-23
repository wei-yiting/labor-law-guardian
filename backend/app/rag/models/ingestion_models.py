"""Future purpose: define RawLawArticle (and related) Pydantic models as the project-wide data contract."""
from enum import Enum
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field, HttpUrl

# --- From law.py ---

class LawCategory(Enum):
    """Law category enum"""
    MOTHER_LAW = "母法"
    SUBSIDIARY_LAW = "子法"
    INTERPRETATION = "函釋"
    CASE = "判例"

class RawLawArticle(BaseModel):
    """
    Data structure of a law article (Data Transfer Object)
    Schema of Scraper outputs.
    Graph Builder reads this schema.
    """
    id: str = Field( 
        description="Unique ID (Graph Node Key), e.g. 'LSA-24' for Labor Standard Act Article 24",
        examples=["LSA-24", "ENF_RULE-10"]
    )
    chapter_no: int | None = Field(
        default=None,
        description="Law chapter number, e.g. 2 for '第二章 勞動契約'. Null if law has no chapters.",
        examples=[2, 11]
    )
    chapter_name: str | None = Field(
        default=None,
        description="Law chapter name, e.g. '勞動契約'. Null if law has no chapters.", 
        examples=["勞動契約", "職業災害補償"]
    )
    article_no: str = Field(
        description="Law article number, e.g. '24' for '第 24 條', '9-1' for '第 9-1 條'", 
        examples=["24", "9-1"]
    )
    summary: str | None = Field(
        default=None,
        description="Generated summary for query purposes",
        examples=["延長工作時間之工資加給"]
    )
    content: str = Field(
        description="Law article content, cleaned of HTML tags and extra whitespace"
    )
    url: HttpUrl = Field(
        description="National Law Database URL of Single Law Article, for Citation"
    )
    
    # Reserved fields (future use: LLM can mark simple concepts at this layer)
    related_concepts: Optional[List[str]] = Field(
        default=[], 
        description="Related concept keywords (reserved)"
    )

class RawLawData(BaseModel):
    category: LawCategory = Field(description="The category of the law (Mother Law or Subsidiary Law)")
    title: str = Field(description="The title of the law")
    last_modified_date: date = Field(
        description="Last modified date of the law",
        examples=["2024-03-27"]
    )
    articles: List[RawLawArticle] = Field(description="List of articles in the law")

# --- From chunk.py ---

class SplitStrategyEnum(str, Enum):
    atomic = "atomic"
    numeric = "numeric"
    contextual = "contextual"
    numeric_contextual = "numeric_contextual"
    parent_child_coarse = "parent_child_coarse"


# --- Fine-Grained Models (v0.0.2) ---

class HierarchyFine(BaseModel):
    article: str
    paragraph: int | None = None
    subparagraph: int | None = None

class ChunkMetadataFine(BaseModel):
    url: HttpUrl
    split_strategy: SplitStrategyEnum
    is_expanded: bool
    citation_title: str
    hierarchy: HierarchyFine
    chapter_no: int | None = None
    chapter_title: str | None = None
    article_no: str

class LawChunkFine(BaseModel):
    chunk_id: str
    parent_id: str
    text: str
    metadata: ChunkMetadataFine


# --- Coarse-Grained Models (v0.0.3) ---

class HierarchyCoarse(BaseModel):
    article: str
    paragraph: int | None = None
    # No subparagraph field for coarse chunks

class ChunkMetadataCoarse(BaseModel):
    url: HttpUrl
    split_strategy: SplitStrategyEnum
    is_expanded: bool
    citation_title: str
    hierarchy: HierarchyCoarse
    chapter_no: int | None = None
    chapter_title: str | None = None
    article_no: str

class LawChunkCoarse(BaseModel):
    chunk_id: str
    parent_id: str
    text: str
    metadata: ChunkMetadataCoarse


# --- Union Type ---
# This allows the chunker to return a mixed list or specific list depending on strategy,
# and the loader to handle both.
LawChunk = LawChunkFine | LawChunkCoarse
