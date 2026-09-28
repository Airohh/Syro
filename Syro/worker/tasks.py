"""Tâches Celery."""

import logging
import time

from app.services.ingestion import ingest_document

from .main import celery_app

logger = logging.getLogger(__name__)


def _metric(name: str, method: str, *args, **labels) -> None:
    """Métriques Prometheus best-effort (jamais bloquantes)."""
    try:
        from app import middleware

        getattr(getattr(middleware, name).labels(**labels), method)(*args)
    except Exception:
        pass


@celery_app.task(name="process_document_upload", bind=True, max_retries=3)
def process_document_upload(self, document_id: int, *_legacy_args):
    """Ingère un document ; retente 3 fois (60 s d'écart) en cas d'échec."""
    start = time.time()
    _metric("active_ingestions", "inc", domain="all")
    try:
        chunk_count = ingest_document(document_id)
    except Exception as exc:
        _metric("document_ingestions_total", "inc", domain="all", status="failed")
        logger.error("Ingestion of document %s failed: %s", document_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)
        raise
    finally:
        _metric("active_ingestions", "dec", domain="all")

    duration = time.time() - start
    _metric("document_ingestions_total", "inc", domain="all", status="complete")
    _metric("document_ingestion_duration_seconds", "observe", duration, domain="all")
    _metric("document_chunks_total", "inc", chunk_count, domain="all")
    logger.info(
        "Document %s ingested: %d chunks in %.1fs", document_id, chunk_count, duration
    )
    return {
        "status": "complete",
        "document_id": document_id,
        "chunk_count": chunk_count,
    }
