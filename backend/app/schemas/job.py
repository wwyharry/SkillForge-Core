from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class JobMode(str, Enum):
    explore = "explore"
    compile = "compile"


class JobStatus(str, Enum):
    created = "created"
    queued = "queued"
    scanning = "scanning"
    explored = "explored"
    parsing = "parsing"
    extracting = "extracting"
    clustering = "clustering"
    packaging = "packaging"
    compiling = "compiling"
    validating = "validating"
    completed = "completed"
    failed = "failed"


class StageProgress(BaseModel):
    name: str
    status: str
    progress: int = 0
    detail: str = ""


class JobConfig(BaseModel):
    include_globs: list[str] = Field(default_factory=list)
    exclude_globs: list[str] = Field(default_factory=list)
    priority_paths: list[str] = Field(default_factory=list)
    max_file_size_mb: int = 100
    enable_ocr: bool = False
    process_code: bool = True
    process_chats: bool = True


class JobCreate(BaseModel):
    name: str
    root_path: str
    goal: str
    mode: JobMode = JobMode.explore
    config: JobConfig = Field(default_factory=JobConfig)


class JobSummary(BaseModel):
    id: str
    name: str
    goal: str
    root_path: str
    mode: JobMode
    status: JobStatus
    progress: int
    current_stage: str
    error_stage: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ParsedDocument(BaseModel):
    id: str
    file_path: str
    file_type: str
    title: str
    excerpt: str
    text_content: str
    sections: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalTrace(BaseModel):
    scope: str
    query: str
    target_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class UsageStatus(BaseModel):
    stage: str
    kind: str
    provider: str = ""
    used: bool = False
    fallback_used: bool = False
    status: str = "idle"
    detail: str = ""


class EvidenceRecord(BaseModel):
    id: str
    task: str
    subtask: str
    capability_hint: str
    confidence: float
    source_path: str
    excerpt: str
    workflow_steps: list[str]
    decision_rules: list[str]
    topic_modules: list[str] = Field(default_factory=list)
    quantitative_signals: list[str] = Field(default_factory=list)
    terminology: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    source_document_id: str = ""


class CapabilityCluster(BaseModel):
    id: str
    name: str
    summary: str
    evidence_ids: list[str]
    core_tasks: list[str]
    rules: list[str]
    suggested_packaging: str


class ResourcePlan(BaseModel):
    filename: str
    purpose: str


class SkillPlan(BaseModel):
    id: str
    skill_name: str
    description_draft: str
    skill_md_topics: list[str]
    trigger_conditions: list[str] = Field(default_factory=list)
    workflow_outline: list[str] = Field(default_factory=list)
    decision_logic: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    quantitative_signals: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    references: list[ResourcePlan]
    scripts: list[ResourcePlan]
    assets: list[ResourcePlan]
    source_evidence_ids: list[str]


class GeneratedFile(BaseModel):
    path: str
    content: str


class GeneratedSkill(BaseModel):
    id: str
    skill_name: str
    description: str
    files: list[GeneratedFile]


class ValidationReport(BaseModel):
    score: int
    summary: str
    checks: list[dict[str, Any]]


class InventorySummary(BaseModel):
    total_files: int
    total_size_bytes: int
    categories: dict[str, int]
    top_extensions: dict[str, int]
    suggested_domains: list[str]
    high_priority_files: list[dict[str, Any]]


class ExportRequest(BaseModel):
    output_dir: str
    overwrite: bool = False


class ExportResult(BaseModel):
    output_dir: str
    written_files: list[str]
    skill_names: list[str]


class JobRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str
    root_path: str
    goal: str
    mode: JobMode
    status: JobStatus = JobStatus.created
    progress: int = 0
    current_stage: str = "created"
    async_task_id: str | None = None
    async_queued_at: datetime | None = None
    error_stage: str | None = None
    error_message: str | None = None
    failed_at: datetime | None = None
    config: JobConfig = Field(default_factory=JobConfig)
    stages: list[StageProgress] = Field(default_factory=list)
    inventory_summary: InventorySummary | None = None
    parsed_documents: list[ParsedDocument] = Field(default_factory=list)
    retrieval_traces: list[RetrievalTrace] = Field(default_factory=list)
    usage_statuses: list[UsageStatus] = Field(default_factory=list)
    evidences: list[EvidenceRecord] = Field(default_factory=list)
    capabilities: list[CapabilityCluster] = Field(default_factory=list)
    skill_plans: list[SkillPlan] = Field(default_factory=list)
    generated_skills: list[GeneratedSkill] = Field(default_factory=list)
    validation_report: ValidationReport | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobCollection(BaseModel):
    jobs: list[JobRecord] = Field(default_factory=list)
