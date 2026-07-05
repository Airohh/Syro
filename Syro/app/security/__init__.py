"""Modules de sécurité."""

# Importer les fonctions de l'ancien module security.py (maintenant auth.py)
from ..auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)

from .upload_validator import (
    validate_file_size,
    ALLOWED_MIME_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_TEXT_SIZE,
    UploadValidationError,
)
from .rate_limiter import (
    RedisRateLimiter,
    chat_rate_limiter,
    doc_upload_rate_limiter,
    auth_rate_limiter,
)
from .headers import SecurityHeadersMiddleware

__all__ = [
    # Ancien module security.py
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    # Nouveau module upload_validator
    "validate_file_size",
    "ALLOWED_MIME_TYPES",
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE",
    "MAX_TEXT_SIZE",
    "UploadValidationError",
    # Nouveau module rate_limiter
    "RedisRateLimiter",
    "chat_rate_limiter",
    "doc_upload_rate_limiter",
    "auth_rate_limiter",
    # Nouveau module headers
    "SecurityHeadersMiddleware",
]
