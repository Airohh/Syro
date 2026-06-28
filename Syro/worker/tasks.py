"""Tâches Celery pour le worker async."""

import sys
from pathlib import Path

# Ajouter le chemin de l'API pour importer les modules partagés
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .main import celery_app
from app.db import db_session
from app.services.ingestion import run_ingestion
import logging
import time

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document_upload", bind=True, max_retries=3)
def process_document_upload(self, document_id: int, organization_id: int, storage_path: str, mime_type: str | None = None, domain: str | None = None):
    """
    Tâche Celery pour traiter l'ingestion d'un document.
    
    Args:
        document_id: ID du document dans la DB
        organization_id: ID de l'organisation
        storage_path: Chemin vers le fichier stocké
        mime_type: Type MIME du fichier
        domain: Domaine forcé (optionnel)
    
    Returns:
        dict: Résultat avec chunk_count et statut
    """
    domain_str = domain or "unknown"
    start_time = time.time()
    
    try:
        logger.info(f"Début ingestion document {document_id} (org: {organization_id}, domain: {domain})")
        
        # Métriques Prometheus
        try:
            from app.middleware import (
                document_ingestions_total,
                active_ingestions,
            )
            document_ingestions_total.labels(domain=domain_str, status="processing").inc()
            active_ingestions.labels(domain=domain_str).inc()
        except (ImportError, Exception) as e:
            logger.debug(f"Prometheus metrics not available: {e}")
        
        # Mettre à jour le statut en "processing"
        with db_session() as conn:
            conn.execute(
                "UPDATE documents SET ingestion_status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (document_id,),
            )
            conn.commit()
        
        # Cœur d'ingestion partagé (extract -> métadonnées -> index Qdrant).
        logger.info(f"Indexation du document {document_id}...")
        chunk_count = run_ingestion(document_id, organization_id, storage_path, mime_type, domain)

        # Mettre à jour le statut en "complete"
        with db_session() as conn:
            conn.execute(
                "UPDATE documents SET ingestion_status = 'complete', chunk_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (chunk_count, document_id),
            )
            conn.commit()
        
        duration = time.time() - start_time
        
        # Métriques Prometheus
        try:
            from app.middleware import (
                document_ingestions_total,
                document_ingestion_duration_seconds,
                document_chunks_total,
                active_ingestions,
            )
            document_ingestions_total.labels(domain=domain_str, status="complete").inc()
            document_ingestion_duration_seconds.labels(domain=domain_str).observe(duration)
            document_chunks_total.labels(domain=domain_str).inc(chunk_count)
            active_ingestions.labels(domain=domain_str).dec()
        except (ImportError, Exception) as e:
            logger.debug(f"Prometheus metrics not available: {e}")
        
        logger.info(f"Ingestion terminée pour document {document_id}: {chunk_count} chunks en {duration:.2f}s")
        
        return {
            "status": "complete",
            "document_id": document_id,
            "chunk_count": chunk_count,
        }
        
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(f"Erreur lors de l'ingestion du document {document_id}: {str(exc)}", exc_info=True)
        
        # Métriques Prometheus pour erreur
        try:
            from app.middleware import (
                document_ingestions_total,
                document_ingestion_duration_seconds,
                active_ingestions,
            )
            document_ingestions_total.labels(domain=domain_str, status="failed").inc()
            document_ingestion_duration_seconds.labels(domain=domain_str).observe(duration)
            active_ingestions.labels(domain=domain_str).dec()
        except (ImportError, Exception) as e:
            logger.debug(f"Prometheus metrics not available: {e}")
        
        # Mettre à jour le statut en "failed"
        try:
            with db_session() as conn:
                conn.execute(
                    "UPDATE documents SET ingestion_status = 'failed', ingestion_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (str(exc), document_id),
                )
                conn.commit()
        except Exception as db_error:
            logger.error(f"Erreur lors de la mise à jour du statut d'erreur: {str(db_error)}")
        
        # Retry automatique si ce n'est pas la dernière tentative
        if self.request.retries < self.max_retries:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries} pour document {document_id}")
            raise self.retry(exc=exc, countdown=60)  # Retry après 60 secondes
        
        # Si toutes les tentatives ont échoué, lever l'exception
        raise

