from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "skillforge",
    broker=settings.broker_url or settings.redis_url,
    backend=settings.result_backend or settings.redis_url,
)

celery_app.conf.update(task_track_started=True)
