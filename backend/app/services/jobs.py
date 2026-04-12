from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.schemas.job import JobCreate, JobRecord, JobStatus, JobSummary, StageProgress, UsageStatus
from app.services.compiler import CompilerService
from app.services.distillation import DistillationService
from app.services.extraction import ExtractionService
from app.services.inventory import InventoryService
from app.services.parsing import ParsingService
from app.services.repository import JobRepository


class JobService:
    def __init__(self) -> None:
        self.repository = JobRepository()
        self.inventory = InventoryService()
        self.parsing = ParsingService()
        self.extraction = ExtractionService()
        self.distillation = DistillationService()
        self.compiler = CompilerService()

    def list_jobs(self) -> list[JobSummary]:
        return [self._to_summary(job) for job in self.repository.list()]

    def create_job(self, payload: JobCreate) -> JobRecord:
        job = JobRecord(
            name=payload.name,
            root_path=payload.root_path,
            goal=payload.goal,
            mode=payload.mode,
            config=payload.config,
            stages=self._default_stages(),
        )
        self.repository.save(job)
        return job

    def get_job(self, job_id: str) -> JobRecord:
        return self.repository.get(job_id)

    def dispatch_job(self, job_id: str) -> dict:
        job = self.repository.get(job_id)
        if settings.use_async_pipeline:
            from app.tasks.job_tasks import run_job_task

            self._mark_queued(job)
            task = run_job_task.delay(job_id)
            job.async_task_id = task.id
            job.async_queued_at = datetime.now(timezone.utc)
            self.repository.save(job)
            return {"job_id": job_id, "queued": True, "task_id": task.id, "status": job.status, "progress": job.progress}
        job = self.run_job(job_id)
        return {"job_id": job.id, "queued": False, "status": job.status, "progress": job.progress}

    def run_job(self, job_id: str) -> JobRecord:
        job = self.repository.get(job_id)
        try:
            job.retrieval_traces = []
            job.usage_statuses = []
            self._update_stage(job, JobStatus.scanning, 12, "Scanning repository and building inventory")
            job.inventory_summary = self.inventory.build_summary(job.root_path, job.config)

            self._update_stage(job, JobStatus.parsing, 32, "Parsing candidate documents")
            candidate_files, parse_usage = self.inventory.discover_candidate_files(job.root_path, job.config, goal=job.goal)
            job.usage_statuses.append(parse_usage)
            job.parsed_documents = self.parsing.parse_files(candidate_files)

            self._update_stage(job, JobStatus.extracting, 56, "Extracting workflow evidence from parsed documents")
            job.evidences, extract_traces, extract_usage = self.extraction.build_evidences(job.parsed_documents)
            job.retrieval_traces.extend(extract_traces)
            job.usage_statuses.extend(extract_usage)

            self._update_stage(job, JobStatus.clustering, 72, "Composing capability clusters")
            job.capabilities, cluster_usage = self.distillation.build_capabilities(job.evidences)
            job.usage_statuses.extend(cluster_usage)

            self._update_stage(job, JobStatus.packaging, 84, "Planning skill packaging")
            job.skill_plans = self.distillation.build_skill_plans(job.capabilities, job.evidences)
            job.usage_statuses.append(UsageStatus(stage="package", kind="system", status="used", used=True, detail=f"Planned {len(job.skill_plans)} skill packages heuristically."))

            self._update_stage(job, JobStatus.compiling, 93, "Compiling generated skills")
            job.generated_skills, compile_traces, compile_usage = self.compiler.compile_skills(job.skill_plans, job.parsed_documents)
            job.retrieval_traces.extend(compile_traces)
            job.usage_statuses.extend(compile_usage)

            self._update_stage(job, JobStatus.validating, 97, "Validating generated skills")
            job.validation_report = self.compiler.validate(job.generated_skills)
            job.usage_statuses.append(UsageStatus(stage="validate", kind="system", status="used", used=True, detail=f"Validated {len(job.generated_skills)} generated skills."))

            self._mark_completed(job)
            self.repository.save(job)
            return job
        except Exception as exc:
            self._mark_failed(job, str(exc))
            raise

    def _default_stages(self) -> list[StageProgress]:
        return [
            StageProgress(name="queue", status="pending", progress=0),
            StageProgress(name="scan", status="pending", progress=0),
            StageProgress(name="parse", status="pending", progress=0),
            StageProgress(name="extract", status="pending", progress=0),
            StageProgress(name="cluster", status="pending", progress=0),
            StageProgress(name="package", status="pending", progress=0),
            StageProgress(name="compile", status="pending", progress=0),
            StageProgress(name="validate", status="pending", progress=0),
        ]

    def _mark_queued(self, job: JobRecord) -> None:
        job.status = JobStatus.queued
        job.progress = 3
        job.current_stage = JobStatus.queued.value
        job.error_stage = None
        job.error_message = None
        job.failed_at = None
        for stage in job.stages:
            if stage.name == "queue":
                stage.status = "running"
                stage.progress = 3
                stage.detail = "Queued for asynchronous processing"
            elif stage.status == "running":
                stage.status = "completed"
                stage.progress = 100
        self.repository.save(job)

    def _update_stage(self, job: JobRecord, status: JobStatus, progress: int, detail: str) -> None:
        job.status = status
        job.progress = progress
        job.current_stage = status.value
        job.error_stage = None
        job.error_message = None
        job.failed_at = None
        stage_name = {
            JobStatus.scanning: "scan",
            JobStatus.parsing: "parse",
            JobStatus.extracting: "extract",
            JobStatus.clustering: "cluster",
            JobStatus.packaging: "package",
            JobStatus.compiling: "compile",
            JobStatus.validating: "validate",
        }.get(status)
        if stage_name:
            for stage in job.stages:
                if stage.name == "queue" and stage.status == "running":
                    stage.status = "completed"
                    stage.progress = 100
                if stage.name == stage_name:
                    stage.status = "running"
                    stage.progress = progress
                    stage.detail = detail
                elif stage.status == "running" and stage.name != stage_name:
                    stage.status = "completed"
                    stage.progress = 100
        self.repository.save(job)

    def _mark_completed(self, job: JobRecord) -> None:
        job.status = JobStatus.completed
        job.progress = 100
        job.current_stage = JobStatus.completed.value
        job.error_stage = None
        job.error_message = None
        job.failed_at = None
        for stage in job.stages:
            stage.status = "completed"
            stage.progress = 100
            if not stage.detail:
                stage.detail = "Completed"

    def _mark_failed(self, job: JobRecord, message: str) -> None:
        job.status = JobStatus.failed
        job.error_stage = job.current_stage
        job.error_message = message[:2000]
        job.failed_at = datetime.now(timezone.utc)
        for stage in job.stages:
            if stage.name == job.current_stage or (job.current_stage == JobStatus.queued.value and stage.name == "queue"):
                stage.status = "failed"
                stage.detail = message[:400]
        self.repository.save(job)

    def _to_summary(self, job: JobRecord) -> JobSummary:
        return JobSummary(
            id=job.id,
            name=job.name,
            goal=job.goal,
            root_path=job.root_path,
            mode=job.mode,
            status=job.status,
            progress=job.progress,
            current_stage=job.current_stage,
            error_stage=job.error_stage,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
