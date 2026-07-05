"""Configuration pour le worker Celery."""

import os
from pathlib import Path

# Chemin racine du projet (parent de worker/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Configuration Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Configuration de la tâche
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

# Configuration des tâches
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max par tâche
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50

# Import des settings de l'API pour partager la config
try:
    import sys

    sys.path.insert(0, str(PROJECT_ROOT))
    from app.config import settings

    # Utiliser les mêmes settings que l'API
    QDRANT_URL = settings.qdrant_url
    DB_PATH = settings.db_path
    DATA_DIR = settings.data_dir
except ImportError:
    # Fallback si l'import échoue
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    DB_PATH = PROJECT_ROOT / "db" / "syro.db"
    DATA_DIR = PROJECT_ROOT / "storage"
