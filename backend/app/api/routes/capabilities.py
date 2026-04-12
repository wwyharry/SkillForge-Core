from fastapi import APIRouter, HTTPException

from app.services.repository import JobRepository

router = APIRouter(prefix="/capabilities", tags=["capabilities"])
repository = JobRepository()


@router.get("/{job_id}")
def get_capabilities(job_id: str):
    try:
        job = repository.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    return job.capabilities
