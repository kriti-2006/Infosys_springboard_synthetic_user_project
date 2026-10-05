"""SQLAlchemy 2.0 models for Milestone 3. PostgreSQL is the target; JSON/Vector degrade on SQLite for tests."""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import settings

JSONType = JSON().with_variant(JSONB(), "postgresql")
VectorType = Vector(settings.EMBEDDING_DIM).with_variant(JSON(), "sqlite")


def _id() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class _Timestamps:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Experiment(Base, _Timestamps):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(200))
    product_description: Mapped[str] = mapped_column(Text)
    target_audience: Mapped[str] = mapped_column(Text, default="")
    research_objectives: Mapped[str] = mapped_column(Text, default="")
    personas = relationship("Persona", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentDocument(Base):
    __tablename__ = "experiment_documents"
    __table_args__ = (UniqueConstraint("experiment_id", "sha256", name="uq_doc_experiment_sha"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(500))
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Persona(Base, _Timestamps):
    __tablename__ = "personas"
    __table_args__ = (UniqueConstraint("experiment_id", "key", name="uq_persona_experiment_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(100))  # Milestone-2 persona id, e.g. "p1"
    name: Mapped[str] = mapped_column(String(200))
    age: Mapped[int] = mapped_column(Integer)
    occupation: Mapped[str] = mapped_column(String(300))
    personality: Mapped[list] = mapped_column(JSONType, default=list)
    behavioral_patterns: Mapped[list] = mapped_column(JSONType, default=list)
    psychological_profile: Mapped[str] = mapped_column(Text, default="")
    segment: Mapped[str] = mapped_column(String(60), default="other", index=True)
    profile: Mapped[dict] = mapped_column(JSONType, default=dict)  # full Milestone-2 Persona JSON
    experiment = relationship("Experiment", back_populates="personas")


class PersonaMemory(Base, _Timestamps):
    """Layers 2/3/5 of memory (long_term | experiment | derived). Layer 1 = Persona row; layer 4 = messages/responses."""
    __tablename__ = "persona_memories"
    __table_args__ = (
        UniqueConstraint("persona_id", "layer", "content_hash", name="uq_memory_dedupe"),
        Index("ix_memory_persona_layer", "persona_id", "layer"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), nullable=True)
    layer: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(40), default="fact")
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(40))
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(80), default="")
    embedding = mapped_column(VectorType, nullable=True)


class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    research_objective: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|running|completed|partial|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    questions = relationship("SurveyQuestion", cascade="all, delete-orphan", order_by="SurveyQuestion.order")


class SurveyPersona(Base):
    __tablename__ = "survey_personas"
    survey_id: Mapped[str] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), primary_key=True)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True)


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"
    __table_args__ = (UniqueConstraint("survey_id", "key", name="uq_question_survey_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    survey_id: Mapped[str] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(100))  # client-supplied questionId, e.g. "q1"
    question: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(30))
    options: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    scale_min: Mapped[int] = mapped_column(Integer, default=1)
    scale_max: Mapped[int] = mapped_column(Integer, default=5)
    order: Mapped[int] = mapped_column(Integer, default=0)


class SurveyResponse(Base, _Timestamps):
    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint("survey_id", "question_id", "persona_id", name="uq_response_survey_question_persona"),
        Index("ix_response_survey_status", "survey_id", "status"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    survey_id: Mapped[str] = mapped_column(ForeignKey("surveys.id", ondelete="CASCADE"))
    question_id: Mapped[str] = mapped_column(ForeignKey("survey_questions.id", ondelete="CASCADE"))
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed|failed
    response: Mapped[str] = mapped_column(Text, default="")
    value: Mapped[object | None] = mapped_column(JSONType, nullable=True)  # normalized typed answer
    sentiment: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Interview(Base, _Timestamps):
    __tablename__ = "interviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|closed


class InterviewMessage(Base):
    __tablename__ = "interview_messages"
    __table_args__ = (
        UniqueConstraint("interview_id", "turn_number", "role", name="uq_message_turn_role"),
        UniqueConstraint("interview_id", "client_message_id", name="uq_message_client_id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    interview_id: Mapped[str] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user|persona
    content: Mapped[str] = mapped_column(Text)
    turn_number: Mapped[int] = mapped_column(Integer)
    client_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    relevant_memory: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    validation: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (Index("ix_insight_experiment_created", "experiment_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    source_type: Mapped[str] = mapped_column(String(30))  # survey|interview|combined
    data: Mapped[dict] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProductUsageScore(Base, _Timestamps):
    __tablename__ = "product_usage_scores"
    __table_args__ = (UniqueConstraint("experiment_id", "persona_id", name="uq_usage_experiment_persona"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(20))
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    factors: Mapped[list | None] = mapped_column(JSONType, nullable=True)
