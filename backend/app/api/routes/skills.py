from fastapi import APIRouter, HTTPException

from app.schemas.job import ExportRequest
from app.services.exporter import ExportService
from app.services.repository import JobRepository

router = APIRouter(prefix="/skills", tags=["skills"])
repository = JobRepository()
exporter = ExportService()


@router.get("/{job_id}/plans")
def get_skill_plans(job_id: str):
    try:
        job = repository.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return job.skill_plans


@router.get("/{job_id}/generated")
def get_generated_skills(job_id: str):
    try:
        job = repository.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return {"generated_skills": job.generated_skills, "validation_report": job.validation_report}


@router.post("/{job_id}/export")
def export_generated_skills(job_id: str, payload: ExportRequest):
    try:
        job = repository.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    if not job.generated_skills:
        raise HTTPException(status_code=400, detail="No generated skills available for export")
    try:
        return exporter.export_generated_skills(job.generated_skills, payload.output_dir, payload.overwrite)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
