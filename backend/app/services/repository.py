from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.models import CapabilityORM, DocumentORM, EvidenceORM, GeneratedSkillORM, JobORM, SkillPlanORM
from app.schemas.job import (
    CapabilityCluster,
    EvidenceRecord,
    GeneratedSkill,
    JobRecord,
    ParsedDocument,
    ResourcePlan,
    RetrievalTrace,
    SkillPlan,
    StageProgress,
    UsageStatus,
    ValidationReport,
)


class RepositoryProtocol(Protocol):
    def save(self, job: JobRecord) -> JobRecord: ...
    def get(self, job_id: str) -> JobRecord: ...
    def list(self) -> Iterable[JobRecord]: ...


class FileJobRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or settings.data_dir / "jobs"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        return self.base_dir / f"{job_id}.json"

    def save(self, job: JobRecord) -> JobRecord:
        job.updated_at = datetime.now(timezone.utc)
        self._path(job.id).write_text(job.model_dump_json(indent=2), encoding="utf-8")
        return job

    def get(self, job_id: str) -> JobRecord:
        path = self._path(job_id)
        if not path.exists():
            raise FileNotFoundError(job_id)
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> Iterable[JobRecord]:
        for path in sorted(self.base_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            yield JobRecord.model_validate_json(path.read_text(encoding="utf-8"))


class DatabaseJobRepository:
    def save(self, job: JobRecord) -> JobRecord:
        with SessionLocal() as session:
            existing = session.get(
                JobORM,
                job.id,
                options=(
                    selectinload(JobORM.documents),
                    selectinload(JobORM.evidences),
                    selectinload(JobORM.capabilities),
                    selectinload(JobORM.skill_plans),
                    selectinload(JobORM.generated_skills),
                ),
            )
            if existing is None:
                existing = JobORM(id=job.id)
                session.add(existing)

            existing.name = job.name
            existing.goal = job.goal
            existing.root_path = job.root_path
            existing.mode = job.mode.value
            existing.status = job.status.value
            existing.progress = job.progress
            existing.current_stage = job.current_stage
            existing.async_task_id = job.async_task_id
            existing.async_queued_at = job.async_queued_at
            existing.error_stage = job.error_stage
            existing.error_message = job.error_message
            existing.failed_at = job.failed_at
            existing.config = job.config.model_dump(mode="json")
            existing.stages = [stage.model_dump(mode="json") for stage in job.stages]
            existing.inventory_summary = job.inventory_summary.model_dump(mode="json") if job.inventory_summary else None
            existing.retrieval_traces = [trace.model_dump(mode="json") for trace in job.retrieval_traces]
            existing.usage_statuses = [status.model_dump(mode="json") for status in job.usage_statuses]
            existing.validation_report = job.validation_report.model_dump(mode="json") if job.validation_report else None
            existing.created_at = job.created_at
            existing.updated_at = datetime.now(timezone.utc)

            existing.documents = [
                DocumentORM(
                    id=document.id,
                    job_id=job.id,
                    file_path=document.file_path,
                    file_type=document.file_type,
                    title=document.title,
                    excerpt=document.excerpt,
                    sections=document.sections,
                    text_content=document.text_content,
                    metadata_json=document.metadata,
                )
                for document in job.parsed_documents
            ]
            existing.evidences = [
                EvidenceORM(
                    id=evidence.id,
                    job_id=job.id,
                    task=evidence.task,
                    subtask=evidence.subtask,
                    capability_hint=evidence.capability_hint,
                    confidence=evidence.confidence,
                    source_path=evidence.source_path,
                    excerpt=evidence.excerpt,
                    workflow_steps=evidence.workflow_steps,
                    decision_rules=evidence.decision_rules,
                    topic_modules=evidence.topic_modules,
                    quantitative_signals=evidence.quantitative_signals,
                    terminology=evidence.terminology,
                    dependencies=evidence.dependencies,
                    exceptions=evidence.exceptions,
                    source_document_id=evidence.source_document_id,
                )
                for evidence in job.evidences
            ]
            existing.capabilities = [
                CapabilityORM(
                    id=capability.id,
                    job_id=job.id,
                    name=capability.name,
                    summary=capability.summary,
                    evidence_ids=capability.evidence_ids,
                    core_tasks=capability.core_tasks,
                    rules=capability.rules,
                    suggested_packaging=capability.suggested_packaging,
                )
                for capability in job.capabilities
            ]
            existing.skill_plans = [
                SkillPlanORM(
                    id=plan.id,
                    job_id=job.id,
                    skill_name=plan.skill_name,
                    description_draft=plan.description_draft,
                    skill_md_topics=plan.skill_md_topics,
                    trigger_conditions=plan.trigger_conditions,
                    workflow_outline=plan.workflow_outline,
                    decision_logic=plan.decision_logic,
                    boundaries=plan.boundaries,
                    key_terms=plan.key_terms,
                    quantitative_signals=plan.quantitative_signals,
                    dependencies=plan.dependencies,
                    exceptions=plan.exceptions,
                    references=[item.model_dump(mode="json") for item in plan.references],
                    scripts=[item.model_dump(mode="json") for item in plan.scripts],
                    assets=[item.model_dump(mode="json") for item in plan.assets],
                    source_evidence_ids=plan.source_evidence_ids,
                )
                for plan in job.skill_plans
            ]
            existing.generated_skills = [
                GeneratedSkillORM(
                    id=skill.id,
                    job_id=job.id,
                    skill_name=skill.skill_name,
                    description=skill.description,
                    files=[file.model_dump(mode="json") for file in skill.files],
                )
                for skill in job.generated_skills
            ]
            session.commit()
        return job

    def get(self, job_id: str) -> JobRecord:
        with SessionLocal() as session:
            row = session.get(
                JobORM,
                job_id,
                options=(
                    selectinload(JobORM.documents),
                    selectinload(JobORM.evidences),
                    selectinload(JobORM.capabilities),
                    selectinload(JobORM.skill_plans),
                    selectinload(JobORM.generated_skills),
                ),
            )
            if row is None:
                raise FileNotFoundError(job_id)
            return self._hydrate(row)

    def list(self) -> Iterable[JobRecord]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(JobORM)
                .options(
                    selectinload(JobORM.documents),
                    selectinload(JobORM.evidences),
                    selectinload(JobORM.capabilities),
                    selectinload(JobORM.skill_plans),
                    selectinload(JobORM.generated_skills),
                )
                .order_by(JobORM.updated_at.desc())
            ).all()
            for row in rows:
                yield self._hydrate(row)

    def _hydrate(self, row: JobORM) -> JobRecord:
        return JobRecord(
            id=row.id,
            name=row.name,
            root_path=row.root_path,
            goal=row.goal,
            mode=row.mode,
            status=row.status,
            progress=row.progress,
            current_stage=row.current_stage,
            async_task_id=row.async_task_id,
            async_queued_at=row.async_queued_at,
            error_stage=row.error_stage,
            error_message=row.error_message,
            failed_at=row.failed_at,
            config=row.config or {},
            stages=[StageProgress.model_validate(stage) for stage in (row.stages or [])],
            inventory_summary=row.inventory_summary or None,
            retrieval_traces=[RetrievalTrace.model_validate(item) for item in (row.retrieval_traces or [])],
            usage_statuses=[UsageStatus.model_validate(item) for item in (row.usage_statuses or [])],
            parsed_documents=[
                ParsedDocument(
                    id=document.id,
                    file_path=document.file_path,
                    file_type=document.file_type,
                    title=document.title,
                    excerpt=document.excerpt,
                    sections=document.sections or [],
                    text_content=document.text_content,
                    metadata=document.metadata_json or {},
                )
                for document in row.documents
            ],
            evidences=[
                EvidenceRecord(
                    id=evidence.id,
                    task=evidence.task,
                    subtask=evidence.subtask,
                    capability_hint=evidence.capability_hint,
                    confidence=evidence.confidence,
                    source_path=evidence.source_path,
                    excerpt=evidence.excerpt,
                    workflow_steps=evidence.workflow_steps or [],
                    decision_rules=evidence.decision_rules or [],
                    topic_modules=evidence.topic_modules or [],
                    quantitative_signals=evidence.quantitative_signals or [],
                    terminology=evidence.terminology or [],
                    dependencies=evidence.dependencies or [],
                    exceptions=evidence.exceptions or [],
                    source_document_id=evidence.source_document_id,
                )
                for evidence in row.evidences
            ],
            capabilities=[
                CapabilityCluster(
                    id=capability.id,
                    name=capability.name,
                    summary=capability.summary,
                    evidence_ids=capability.evidence_ids or [],
                    core_tasks=capability.core_tasks or [],
                    rules=capability.rules or [],
                    suggested_packaging=capability.suggested_packaging,
                )
                for capability in row.capabilities
            ],
            skill_plans=[
                SkillPlan(
                    id=plan.id,
                    skill_name=plan.skill_name,
                    description_draft=plan.description_draft,
                    skill_md_topics=plan.skill_md_topics or [],
                    trigger_conditions=plan.trigger_conditions or [],
                    workflow_outline=plan.workflow_outline or [],
                    decision_logic=plan.decision_logic or [],
                    boundaries=plan.boundaries or [],
                    key_terms=plan.key_terms or [],
                    quantitative_signals=plan.quantitative_signals or [],
                    dependencies=plan.dependencies or [],
                    exceptions=plan.exceptions or [],
                    references=[ResourcePlan.model_validate(item) for item in (plan.references or [])],
                    scripts=[ResourcePlan.model_validate(item) for item in (plan.scripts or [])],
                    assets=[ResourcePlan.model_validate(item) for item in (plan.assets or [])],
                    source_evidence_ids=plan.source_evidence_ids or [],
                )
                for plan in row.skill_plans
            ],
            generated_skills=[
                GeneratedSkill.model_validate(
                    {
                        "id": skill.id,
                        "skill_name": skill.skill_name,
                        "description": skill.description,
                        "files": skill.files or [],
                    }
                )
                for skill in row.generated_skills
            ],
            validation_report=ValidationReport.model_validate(row.validation_report) if row.validation_report else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


class JobRepository:
    def __init__(self) -> None:
        self.impl: RepositoryProtocol = DatabaseJobRepository() if settings.use_database_persistence else FileJobRepository()

    def save(self, job: JobRecord) -> JobRecord:
        return self.impl.save(job)

    def get(self, job_id: str) -> JobRecord:
        return self.impl.get(job_id)

    def list(self) -> Iterable[JobRecord]:
        return self.impl.list()
