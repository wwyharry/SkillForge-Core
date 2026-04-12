from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base


class JobORM(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    root_path: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False, default="created")
    async_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    async_queued_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    stages: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    inventory_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    retrieval_traces: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    usage_statuses: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    documents: Mapped[list["DocumentORM"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    evidences: Mapped[list["EvidenceORM"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    capabilities: Mapped[list["CapabilityORM"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    skill_plans: Mapped[list["SkillPlanORM"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    generated_skills: Mapped[list["GeneratedSkillORM"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class DocumentORM(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    sections: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    job: Mapped[JobORM] = relationship(back_populates="documents")


class EvidenceORM(Base):
    __tablename__ = "evidences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    subtask: Mapped[str] = mapped_column(Text, nullable=False)
    capability_hint: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_steps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    decision_rules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    topic_modules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    quantitative_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    terminology: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exceptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_document_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    job: Mapped[JobORM] = relationship(back_populates="evidences")


class CapabilityORM(Base):
    __tablename__ = "capabilities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    core_tasks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    suggested_packaging: Mapped[str] = mapped_column(String(64), nullable=False)

    job: Mapped[JobORM] = relationship(back_populates="capabilities")


class SkillPlanORM(Base):
    __tablename__ = "skill_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description_draft: Mapped[str] = mapped_column(Text, nullable=False)
    skill_md_topics: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    trigger_conditions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    workflow_outline: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    decision_logic: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    boundaries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    key_terms: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    quantitative_signals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dependencies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    exceptions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    references: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    scripts: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    assets: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    source_evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    job: Mapped[JobORM] = relationship(back_populates="skill_plans")


class GeneratedSkillORM(Base):
    __tablename__ = "generated_skills"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)

    job: Mapped[JobORM] = relationship(back_populates="generated_skills")
