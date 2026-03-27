from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "smart_job_tracker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_track_started=True,
    include=["app.tasks.scrape_job", "app.tasks.reminders"],
)

