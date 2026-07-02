import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# We use Redis as both the broker (message queue) and the result backend.
# The URL defaults to localhost for local development.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

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
