"""Tâches Celery pour le worker async."""

import sys
from pathlib import Path

# Ajouter le chemin de l'API pour importer les modules partagés
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from .main import celery_app
from app.db import db_session
from app.services.file_extractor import extract_text_from_bytes
from app.services.rag import index_document_content
import json
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
    path = Path(storage_path)
    
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
        
        # Lire et extraire le texte
        content_bytes = path.read_bytes()
        text = extract_text_from_bytes(content_bytes, path.name, mime_type)
        
        if not text.strip():
            raise ValueError("Document vide après extraction")
        
        # Extraire les métadonnées depuis la DB
        with db_session() as conn:
            doc_row = conn.execute(
                "SELECT filename, source_type, tags FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            
            if not doc_row:
                raise ValueError(f"Document {document_id} non trouvé dans la DB")
            
            source_type = doc_row["source_type"] or "unknown"
            tags_json = doc_row["tags"]
            try:
                tags = json.loads(tags_json) if tags_json else []
            except (json.JSONDecodeError, TypeError):
                tags = []
            
            # Construire les métadonnées
            metadata = {
                "source_type": source_type,
                "tags": tags,
            }
            
            # Si domaine forcé, l'utiliser
            if domain:
                metadata["domain"] = domain
            
            # Inférer le type depuis le nom de fichier
            filename_lower = doc_row["filename"].lower()
            if any(keyword in filename_lower for keyword in ["snowflake", "snow"]):
                metadata["type"] = "snowflake"
            elif any(keyword in filename_lower for keyword in ["airflow", "dag"]):
                metadata["type"] = "airflow"
            elif any(keyword in filename_lower for keyword in ["databricks", "spark"]):
                metadata["type"] = "databricks"
            elif any(keyword in filename_lower for keyword in ["azure", "synapse"]):
                metadata["type"] = "azure"
            elif any(keyword in filename_lower for keyword in ["terraform", "tf"]):
                metadata["type"] = "terraform"
            elif any(keyword in filename_lower for keyword in ["sql", "query"]):
                metadata["type"] = "sql"
            else:
                metadata["type"] = "general"
            
            # Inférer la difficulté
            if any(tag.lower() in ["beginner", "intro", "basics"] for tag in tags):
                metadata["difficulty"] = "beginner"
            elif any(tag.lower() in ["advanced", "expert", "complex"] for tag in tags):
                metadata["difficulty"] = "expert"
            else:
                metadata["difficulty"] = "intermediate"
        
        # Indexer le document (chunking + embeddings + upsert Qdrant)
        logger.info(f"Indexation du document {document_id}...")
        chunk_count = index_document_content(document_id, organization_id, text, metadata=metadata)
        
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

