"""Worker Celery : ingestion asynchrone des documents.

Lancement : celery -A worker.main worker --loglevel=info
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from celery import Celery  # noqa: E402

from app.config import settings  # noqa: E402

celery_app = Celery("syro_worker")
celery_app.conf.update(
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # une tâche n'est acquittée qu'une fois terminée
    task_reject_on_worker_lost=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    broker_connection_retry_on_startup=True,
)

from . import tasks  # noqa: E402, F401  (enregistre les tâches)

if __name__ == "__main__":
    celery_app.start()
