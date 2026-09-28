"""Mise en file de l'ingestion : Celery (worker) si dispo, sinon BackgroundTasks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from ..config import settings

if TYPE_CHECKING:
    from celery import Celery
    from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

_celery_app: "Celery | None" = None


def get_celery_app() -> "Celery":
    global _celery_app
    if _celery_app is None:
        from celery import Celery

        _celery_app = Celery("syro_api")
        _celery_app.conf.update(
            broker_url=settings.celery_broker_url,
            result_backend=settings.celery_result_backend,
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            enable_utc=True,
            broker_connection_timeout=2,
        )
    return _celery_app


def enqueue_document_ingestion(
    document_id: int,
    background_tasks: Optional["BackgroundTasks"] = None,
) -> str:
    """Retourne l'id de tâche Celery, ou un marqueur si exécuté localement."""
    from .ingestion import process_document

    if not settings.celery_task_always_eager:
        try:
            task = get_celery_app().send_task(
                "process_document_upload", args=[document_id]
            )
            return task.id
        except Exception as e:
            logger.warning("Celery unavailable, ingesting in-process: %s", e)

    if background_tasks is not None:
        background_tasks.add_task(process_document, document_id)
        return "background-task"
    process_document(document_id)
    return "sync"
