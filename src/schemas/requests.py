from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """User request payload for design research.

    Mirrors the assignment contract. Provider/runtime options are configured
    elsewhere (not part of this schema).
    """

    question: str = Field(..., min_length=5, description="Design research question")
    max_results: int = Field(10, ge=1, le=20, description="Maximum number of results to consider")
    include_images: bool = Field(True, description="Whether to include images for examples when available")


