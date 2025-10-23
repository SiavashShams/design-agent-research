"""Pydantic schemas for evaluation results.

Moved from src/evaluation/ to src/schemas/ to centralize data contracts.
"""

from typing import List
from pydantic import BaseModel, Field


class CategoryScore(BaseModel):
    """Score for a specific evaluation category."""

    score: float = Field(..., ge=0.0, le=10.0, description="Score from 0-10")
    reasoning: str = Field(..., description="Explanation for this score")
    strengths: List[str] = Field(default_factory=list, description="What was done well")
    weaknesses: List[str] = Field(default_factory=list, description="What could be improved")


class EvaluationScores(BaseModel):
    """Detailed scores across all evaluation dimensions."""

    relevance: CategoryScore = Field(
        ..., description="How relevant are search results and recommendations to the query?"
    )
    synthesis_quality: CategoryScore = Field(
        ..., description="Quality of synthesis - original insights vs copy-paste, new information"
    )
    completeness: CategoryScore = Field(
        ..., description="Does it answer the question? Are all required sections present and detailed?"
    )
    actionability: CategoryScore = Field(
        ..., description="Is the information actionable and appropriate detail level for designers?"
    )
    citations: CategoryScore = Field(
        ..., description="Quality and accuracy of citations, proper source attribution"
    )
    accessibility: CategoryScore = Field(
        ..., description="Coverage of accessibility considerations, WCAG references"
    )
    examples_quality: CategoryScore = Field(
        ..., description="Quality and relevance of examples, working URLs, visual references"
    )


class EvaluationResult(BaseModel):
    """Complete evaluation result with scores and critique."""

    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall score out of 100")
    scores: EvaluationScores = Field(..., description="Detailed category scores")

    overall_critique: str = Field(..., description="High-level summary of the evaluation")

    key_strengths: List[str] = Field(default_factory=list, description="Top 3-5 strengths of this response")
    key_weaknesses: List[str] = Field(default_factory=list, description="Top 3-5 areas for improvement")
    recommendations: List[str] = Field(default_factory=list, description="Specific recommendations to improve the response")

    query_type_appropriateness: str = Field(
        ..., description="How well does the response match the query type (pattern/accessibility/inspiration/feasibility)?"
    )


__all__ = ["EvaluationResult", "EvaluationScores", "CategoryScore"]


