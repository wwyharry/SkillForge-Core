from fastapi import APIRouter, HTTPException

from app.services.repository import JobRepository

router = APIRouter(prefix="/evidences", tags=["evidences"])
repository = JobRepository()


@router.get("/{job_id}")
def get_evidences(job_id: str):
    try:
        job = repository.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return job.evidences
