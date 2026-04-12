from app.tasks.celery_app import celery_app


@celery_app.task(name="skillforge.run_job")
def run_job_task(job_id: str) -> dict:
    from app.services.jobs import JobService

    job = JobService().run_job(job_id)
    return {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress,
        "error_stage": job.error_stage,
        "error_message": job.error_message,
    }
