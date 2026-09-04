"""Pydantic schemas for the reports API."""

from datetime import date as date_type
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
class ReportCreate(BaseModel):
    report_text: str = Field(min_length=1, max_length=20_000)
    report_type: Optional[str] = Field(default=None, max_length=32)
    date: Optional[date_type] = None
    site: Optional[str] = Field(default=None, max_length=128)
    activity: Optional[str] = Field(default=None, max_length=128)

    @field_validator("report_text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Report text cannot be empty")
        return v


class AnalyzeRequest(ReportCreate):
    store: bool = True


class ReviewUpdate(BaseModel):
    reviewer: Optional[str] = Field(default=None, max_length=128)
    decision: Optional[Literal["confirmed", "rejected", "edited"]] = None
    corrected_priority: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = None
    corrected_rule: Optional[str] = Field(default=None, max_length=64)
    comments: Optional[str] = Field(default=None, max_length=4000)
    mark_reviewed: bool = False


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
class AnalysisOut(BaseModel):
    id: int
    report_id: int
    sif_potential: bool
    confidence: Optional[float] = None
    priority: Optional[str] = None
    hazard: Optional[str] = None
    potential_consequence: Optional[str] = None
    barrier_failure: Optional[list[str]] = None
    life_saving_rule: Optional[str] = None
    activity: Optional[str] = None
    location: Optional[str] = None
    equipment: Optional[list[str]] = None
    unsafe_type: Optional[str] = None
    evidence: Optional[list[str]] = None
    rule_conditions: Optional[list[dict[str, Any]]] = None
    modified_fields: Optional[list[dict[str, Any]]] = None
    explanation: Optional[str] = None
    recommended_follow_up: Optional[str] = None
    summary: Optional[str] = None
    suggested_actions: Optional[list[str]] = None
    languages: Optional[list[str]] = None
    uncertainty_note: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    id: int
    report_id: int
    reviewer: Optional[str] = None
    decision: Optional[str] = None
    corrected_priority: Optional[str] = None
    corrected_rule: Optional[str] = None
    comments: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class SimilarReportOut(BaseModel):
    id: int
    report_id: str
    similarity: float
    common_hazard: Optional[str] = None
    common_activity: Optional[str] = None
    common_barrier: Optional[list[str]] = None
    common_rule: Optional[str] = None
    # Review context of the matched report — lets the UI surface a *solved*
    # similar case (site A) as the reference for the current one (site B).
    site: Optional[str] = None
    decision: Optional[str] = None
    reviewer: Optional[str] = None
    comments: Optional[str] = None
    corrected_rule: Optional[str] = None
    corrected_priority: Optional[str] = None
    reviewed_at: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    report_id: str
    report_text: str
    report_type: Optional[str] = None
    date: Optional[date_type] = None
    site: Optional[str] = None
    activity: Optional[str] = None
    is_demo: bool
    source: Optional[str] = Field(default=None, max_length=64)
    source_id: Optional[str] = Field(default=None, max_length=64)
    processing_status: str = "analyzed"
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportDetailOut(ReportOut):
    analysis: Optional[AnalysisOut] = None
    review: Optional[ReviewOut] = None
    review_status: str = "pending"
    similar_reports: list[SimilarReportOut] = []
    # Set when another stored report is a near-copy of this one (same incident
    # reported twice / the same row imported twice). Computed from the
    # similarity engine — never from the file's own IDs.
    duplicate_of: Optional[SimilarReportOut] = None


class AnalysisResultOut(BaseModel):
    """Result of a single analysis (not yet stored or just computed)."""

    sif_potential: bool
    confidence: Optional[float] = None
    priority: Optional[str] = None
    hazard: Optional[str] = None
    hazards: list[str] = []
    potential_consequence: Optional[str] = None
    barrier_failure: list[str] = []
    life_saving_rule: Optional[str] = None
    activity: Optional[str] = None
    location: Optional[str] = None
    equipment: list[str] = []
    unsafe_type: Optional[str] = None
    evidence: list[str] = []
    rule_conditions: list[dict[str, Any]] = []
    explanation: Optional[str] = None
    recommended_follow_up: Optional[str] = None
    summary: Optional[str] = None
    suggested_actions: list[str] = []
    languages: list[str] = []
    model: Optional[str] = None
    llm_refined: bool = False
    uncertainty_note: Optional[str] = None
    priority_factors: dict[str, Any] = {}