"""Celery application configured to use Redis from environment variables."""
from __future__ import annotations

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery("python_engine", broker=BROKER_URL, backend=RESULT_BACKEND)
celery_app.conf.update(task_track_started=True, result_expires=3600)


@celery_app.task(name="python_engine.process_event")
def process_event(event: dict) -> dict:
    """Simple Celery task that echoes processed event metadata."""
    return {
        "event_id": event.get("id"),
        "status": "processed",
        "payload": event,
    }
