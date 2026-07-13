from celery import Celery
from app.config import get_settings

# We use Redis as both the broker (message queue) and the result backend.
REDIS_URL = get_settings().redis_url

celery_app = Celery(
    "kundali_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=4  # Allows multiple map-reduce chains to run
)
