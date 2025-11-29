"""Point d'entrée pour le worker Celery."""

from celery import Celery
from .config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    CELERY_TASK_SERIALIZER,
    CELERY_RESULT_SERIALIZER,
    CELERY_ACCEPT_CONTENT,
    CELERY_TIMEZONE,
    CELERY_ENABLE_UTC,
    CELERY_TASK_ACKS_LATE,
    CELERY_TASK_REJECT_ON_WORKER_LOST,
    CELERY_TASK_TIME_LIMIT,
    CELERY_TASK_SOFT_TIME_LIMIT,
    CELERY_WORKER_PREFETCH_MULTIPLIER,
    CELERY_WORKER_MAX_TASKS_PER_CHILD,
)

# Créer l'application Celery
celery_app = Celery("syro_worker")

# Configuration
celery_app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer=CELERY_TASK_SERIALIZER,
    result_serializer=CELERY_RESULT_SERIALIZER,
    accept_content=CELERY_ACCEPT_CONTENT,
    timezone=CELERY_TIMEZONE,
    enable_utc=CELERY_ENABLE_UTC,
    task_acks_late=CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=CELERY_TASK_REJECT_ON_WORKER_LOST,
    task_time_limit=CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=CELERY_TASK_SOFT_TIME_LIMIT,
    worker_prefetch_multiplier=CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=CELERY_WORKER_MAX_TASKS_PER_CHILD,
)

# Importer les tâches pour qu'elles soient enregistrées
from . import tasks  # noqa: E402, F401

if __name__ == "__main__":
    celery_app.start()

