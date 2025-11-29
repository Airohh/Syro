"""Client Celery pour enqueue des tâches depuis l'API."""

from typing import TYPE_CHECKING, Optional

from ..config import settings

if TYPE_CHECKING:
    from celery import Celery
    from fastapi import BackgroundTasks

# Lazy import pour éviter les erreurs si Celery n'est pas installé
_celery_app: "Celery | None" = None

# BackgroundTasks de FastAPI comme fallback (sera injecté depuis les routes)
_background_tasks: Optional["BackgroundTasks"] = None

def get_celery_app() -> "Celery":
    """Obtenir l'application Celery (singleton)."""
    global _celery_app
    
    if _celery_app is None:
        try:
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
            )
        except ImportError:
            raise ImportError(
                "Celery n'est pas installé. Installez-le avec: pip install celery redis"
            )
    
    return _celery_app

def set_background_tasks(background_tasks: "BackgroundTasks") -> None:
    """Définir les BackgroundTasks de FastAPI pour le fallback."""
    global _background_tasks
    _background_tasks = background_tasks

def enqueue_document_ingestion(document_id: int, organization_id: int, storage_path: str, mime_type: str | None = None, domain: str | None = None, background_tasks: Optional["BackgroundTasks"] = None) -> str:
    """
    Enqueue une tâche d'ingestion de document.
    
    Args:
        document_id: ID du document
        organization_id: ID de l'organisation
        storage_path: Chemin vers le fichier
        mime_type: Type MIME
        domain: Domaine forcé
        background_tasks: BackgroundTasks de FastAPI (optionnel, pour fallback)
    
    Returns:
        str: Task ID Celery ou identifiant de tâche
    """
    # Si Celery est désactivé (mode dev), utiliser BackgroundTasks
    if settings.celery_task_always_eager:
        # Utiliser BackgroundTasks si disponible, sinon exécuter directement (non recommandé)
        if background_tasks or _background_tasks:
            from ..services.ingestion import process_document
            tasks = background_tasks or _background_tasks
            tasks.add_task(process_document, document_id, organization_id, storage_path, mime_type, domain)
            return "background-task-execution"
        else:
            # Fallback: exécuter directement (bloquant, à éviter)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Celery désactivé et BackgroundTasks non disponible, exécution synchrone (bloquante)")
            from ..services.ingestion import process_document
            try:
                process_document(document_id, organization_id, storage_path, mime_type, domain)
                return "eager-execution"
            except Exception as e:
                logger.error(f"Erreur lors du traitement synchrone du document {document_id}: {e}", exc_info=True)
                return "eager-execution-error"
    
    # Sinon, essayer d'utiliser Celery
    try:
        celery_app = get_celery_app()
        task = celery_app.send_task(
            "process_document_upload",
            args=[document_id, organization_id, storage_path, mime_type, domain],
        )
        return task.id
    except Exception as e:
        # Si Celery/Redis n'est pas disponible, utiliser BackgroundTasks comme fallback
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Celery/Redis non disponible, basculement vers BackgroundTasks: {e}")
        
        # Utiliser BackgroundTasks de FastAPI (non-bloquant)
        if background_tasks or _background_tasks:
            from ..services.ingestion import process_document
            tasks = background_tasks or _background_tasks
            tasks.add_task(process_document, document_id, organization_id, storage_path, mime_type, domain)
            return "background-task-fallback"
        else:
            # Dernier recours: exécuter directement (bloquant, à éviter)
            logger.error("BackgroundTasks non disponible, exécution synchrone (bloquante)")
            try:
                from ..services.ingestion import process_document
                process_document(document_id, organization_id, storage_path, mime_type, domain)
                return "fallback-sync-execution"
            except Exception as process_error:
                logger.error(f"Erreur lors du traitement synchrone de secours du document {document_id}: {process_error}", exc_info=True)
                return "fallback-sync-execution-error"

