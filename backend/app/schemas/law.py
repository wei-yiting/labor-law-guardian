"""Future purpose: define LawArticle (and related) Pydantic models as the project-wide data contract."""
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List

class LawCategory(Enum):
    """Law category enum"""
    MOTHER_LAW = "母法"
    SUBSIDIARY_LAW = "子法"
    INTERPRETATION = "函釋"
    CASE = "判例"

class LawArticle(BaseModel):
    """
    Data structure of a law article (Data Transfer Object)
    Schema of Scraper outputs.
    Graph Builder reads this schema.
    """
    id: str = Field( 
        description="Unique ID (Graph Node Key), e.g. 'LSA-24' for Labor Standard Act Article 24",
        examples=["LSA-24", "ENF_RULE-10"]
    )
    chapter_no: int = Field(
        description="Law chapter number, e.g. 2 for '第二章 勞動契約'",
        examples=[2, 11]
    )
    chapter_name: str = Field(
        description="Law chapter name, e.g. '勞動契約' for '第二章 勞動契約', '職業災害補償' for '第七章 職業災害補償'", 
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

class LawData(BaseModel):
    category: LawCategory = Field(
        description="Law category, e.g. 母法 for '勞動基準法', 細則 for '勞動基準法施行細則'", 
        examples=["母法", "細則", "函釋", "判例"]
    )
    title: str = Field(
        description="Law title, e.g. '勞動基準法', '勞動基準法施行細則'", 
        examples=["勞動基準法", "勞動基準法施行細則"]
    )
    articles: List[LawArticle]