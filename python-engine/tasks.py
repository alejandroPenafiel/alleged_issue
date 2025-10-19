"""Celery tasks for the Python engine."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery(
    "python_engine",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.task_routes = {
    "python_engine.tasks.process_datapoint": {"queue": "engine"},
}


@celery_app.task(name="python_engine.tasks.process_datapoint")
def process_datapoint(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Simple example task that enriches a datapoint.

    The task stamps the payload with metadata so downstream workers can
    use Redis pub/sub to notify agents or persist the output elsewhere.
    """

    augmented = dict(payload)
    augmented.setdefault("processed_at", datetime.utcnow().isoformat())
    augmented.setdefault("status", "processed")
    return augmented
