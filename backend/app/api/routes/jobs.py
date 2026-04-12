import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.job import JobCreate
from app.services.jobs import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])
service = JobService()
TERMINAL_STATUSES = {"completed", "failed"}


@router.get("")
def list_jobs():
    return service.list_jobs()


@router.post("")
def create_job(payload: JobCreate):
    return service.create_job(payload)


@router.get("/{job_id}")
def get_job(job_id: str):
    try:
        return service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/{job_id}/status")
def get_job_status(job_id: str):
    try:
        job = service.get_job(job_id)
        return {
            "id": job.id,
            "status": job.status,
            "progress": job.progress,
            "current_stage": job.current_stage,
            "async_task_id": job.async_task_id,
            "error_stage": job.error_stage,
            "error_message": job.error_message,
            "failed_at": job.failed_at,
            "updated_at": job.updated_at,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@router.get("/{job_id}/events")
async def stream_job_status(job_id: str):
    try:
        service.get_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc

    async def event_stream():
        last_payload = None
        while True:
            try:
                job = service.get_job(job_id)
            except FileNotFoundError:
                yield "event: error\ndata: {\"detail\": \"Job not found\"}\n\n"
                return

            payload = {
                "id": job.id,
                "status": job.status,
                "progress": job.progress,
                "current_stage": job.current_stage,
                "async_task_id": job.async_task_id,
                "error_stage": job.error_stage,
                "error_message": job.error_message,
                "failed_at": job.failed_at.isoformat() if job.failed_at else None,
                "updated_at": job.updated_at.isoformat(),
            }
            encoded = json.dumps(payload)
            if encoded != last_payload:
                yield f"event: status\ndata: {encoded}\n\n"
                last_payload = encoded

            if job.status in TERMINAL_STATUSES:
                return

            await asyncio.sleep(1.5)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{job_id}/run")
def run_job(job_id: str):
    try:
        return service.run_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{job_id}/retry")
def retry_job(job_id: str):
    try:
        return service.run_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{job_id}/dispatch")
def dispatch_job(job_id: str):
    try:
        return service.dispatch_job(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
