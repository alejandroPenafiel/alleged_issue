"""Celery application and task definitions for the Python engine."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from celery import Celery

LOGGER = logging.getLogger(__name__)


def create_celery_app() -> Celery:
    broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    backend_url = os.getenv("CELERY_RESULT_BACKEND", broker_url)
    app = Celery("engine", broker=broker_url, backend=backend_url)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        worker_max_tasks_per_child=100,
    )
    return app


celery_app = create_celery_app()


@celery_app.task(name="engine.process_event")
def process_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist processed events or enrich them in the background worker.

    In a production deployment the body of this task would call out to long
    running tools (vector stores, LLMs, etc.).  Here we keep it simple and only
    echo the message to make the contract explicit.
    """

    LOGGER.info("Processing event asynchronously: %s", json.dumps(payload, sort_keys=True))
    # Return the payload so that callers can fetch the enriched information
    # via `AsyncResult.get()` if needed.
    return payload
