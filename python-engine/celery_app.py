import os
from celery import Celery

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

celery_app = Celery(
    "python_engine",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)


@celery_app.task(name="python_engine.process_payload")
def process_payload(payload: dict) -> dict:
    """Simple Celery task to demonstrate offloading heavier reasoning."""
    enriched = {
        "raw": payload,
        "score": payload.get("score", 0) * 1.5,
        "tags": sorted(payload.get("tags", [])),
    }
    return enriched
