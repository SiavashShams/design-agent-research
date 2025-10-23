from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field


class Example(BaseModel):
    """Concrete example reference with optional image."""

    title: str
    url: HttpUrl
    description: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    source_domain: Optional[str] = None


class Considerations(BaseModel):
    """Consideration buckets to help designers make tradeoffs."""

    tradeoffs: List[str] = Field(default_factory=list)
    accessibility: List[str] = Field(default_factory=list)
    performance: List[str] = Field(default_factory=list)
    browser_support: List[str] = Field(default_factory=list)


class Source(BaseModel):
    """Citation metadata used for attribution and ranking context."""

    title: str
    url: HttpUrl
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    relevance_score: Optional[float] = None


class DesignResearchResponse(BaseModel):
    """Agent response structure per assignment contract."""

    query_classification: Optional[str] = Field(
        default=None, description="pattern | accessibility | inspiration | feasibility"
    )
    summary: str
    best_practices: List[str]
    examples: List[Example]
    considerations: Considerations
    sources: List[Source]


__all__ = [
    "Example",
    "Considerations",
    "Source",
    "DesignResearchResponse",
]


