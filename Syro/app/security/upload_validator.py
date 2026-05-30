"""Validation stricte des fichiers uploadés."""

from fastapi import HTTPException, UploadFile, status
from typing import List

from ..config import settings

# Import optionnel de python-magic (nécessite libmagic système)
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    # python-magic non disponible (libmagic manquant sur Windows notamment)
    MAGIC_AVAILABLE = False
    magic = None

# Types MIME autorisés
ALLOWED_MIME_TYPES = {
    # Documents texte
    "text/plain",
    "text/markdown",
    "text/csv",
    # Documents Office
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    # Autres
    "application/json",
    "application/xml",
    "text/xml",
    "text/html",
}

# Extensions autorisées (backup si MIME type échoue)
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".html",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
}

# Taille maximale par défaut (100 MB)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

# Taille maximale pour texte brut (10 MB)
MAX_TEXT_SIZE = 10 * 1024 * 1024  # 10 MB

class UploadValidationError(Exception):
    """Exception pour erreurs de validation d'upload."""
    pass

def validate_file_size(file: UploadFile, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Valider la taille d'un fichier.

    Args:
        file: Fichier uploadé (après lecture, file.size est disponible)
        max_size: Taille maximale en bytes

    Raises:
        HTTPException: Si le fichier est trop gros
    """
    size: int | None = getattr(file, "size", None)
    if size is None:
        # Fallback : lire la position courante du fichier sous-jacent
        try:
            f = file.file
            current = f.tell()
            f.seek(0, 2)
            size = f.tell()
            f.seek(current)
        except Exception:
            return  # Impossible de déterminer la taille, on laisse passer

    if size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Fichier trop volumineux. Taille maximale : {max_mb} MB.",
        )
