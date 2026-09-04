"""SQLAlchemy entities for the SIF precursor platform.

Tables: reports, analyses, reviews, life_saving_rules, embeddings.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    report_text: Mapped[str] = mapped_column(Text)
    report_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    site: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    activity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    # Provenance: where the report came from ("demo", "manual", "upload", ...).
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Lifecycle: "pending" (raw row stored, not yet analyzed) / "analyzed" /
    # "failed". Lets the UI show ingestion/processing progress from the DB.
    processing_status: Mapped[str] = mapped_column(String(16), default="analyzed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), unique=True, index=True
    )
    sif_potential: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    hazard: Mapped[str | None] = mapped_column(String(128), nullable=True)
    potential_consequence: Mapped[str | None] = mapped_column(String(256), nullable=True)
    barrier_failure: Mapped[list | None] = mapped_column(JSON, nullable=True)
    life_saving_rule: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    activity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Plain-language narrative + corrective-action checklist + detected languages.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    languages: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Reviewer-learned-signal note (feedback loop) or LLM honesty note.
    uncertainty_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    report: Mapped["Report"] = relationship(back_populates="analysis")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    corrected_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    corrected_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    report: Mapped["Report"] = relationship(back_populates="reviews")


class LifeSavingRule(Base):
    __tablename__ = "life_saving_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), unique=True, index=True
    )
    embedding: Mapped[list] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestJob(Base):
    """One dataset-import run. Lets the UI show live processing progress that
    is persisted in the database (rows are committed in batches as they are
    analyzed, so partial results appear before the job finishes)."""

    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running/done/error
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    imported: Mapped[int] = mapped_column(Integer, default=0)
    skipped_empty: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    sif_potential: Mapped[int] = mapped_column(Integer, default=0)
    high_priority: Mapped[int] = mapped_column(Integer, default=0)
    mapping: Mapped[list | None] = mapped_column(JSON, nullable=True)
    failures: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_report_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Feedback(Base):
    """One HSE review decision stored as a labeled training example.

    Keeps a snapshot of what the AI predicted at review time plus what the
    human decided, so offline training / evaluation can compare fairly even
    after the model changes.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    reviewer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # AI snapshot at review time.
    ai_sif: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ai_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Human label (SIF: True = confirm, False = reject, None = no SIF judgment).
    human_sif: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    human_priority: Mapped[str | None] = mapped_column(String(16), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    report: Mapped["Report"] = relationship()


class TrainingRun(Base):
    """Result of one 'train on reviewed labels' run.

    Stores agreement metrics against human labels plus the learned signals
    (terms HSE reviewers repeatedly linked to SIF). Kept small — this is a
    prototype of a feedback -> retraining loop, not a model registry.
    """

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)