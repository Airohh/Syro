"""Tests pour la validation des uploads (app.security.upload_validator).

Cible l'API réelle du module : validate_file_size + constantes.
Le sniff libmagic a été retiré du code ; aucun test n'en dépend.
"""

import io
import types

import pytest
from fastapi import HTTPException

from app.security.upload_validator import (
    validate_file_size,
    ALLOWED_MIME_TYPES,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_TEXT_SIZE,
    UploadValidationError,
)


def _file_with_size(size):
    """UploadFile-like exposant directement l'attribut .size."""
    return types.SimpleNamespace(size=size)


class _FileWithoutSize:
    """UploadFile-like sans .size : force le fallback seek/tell sur .file."""

    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)


class TestValidateFileSize:
    def test_under_limit_passes(self):
        # Ne lève pas
        validate_file_size(_file_with_size(1024), max_size=MAX_FILE_SIZE)

    def test_over_limit_raises_413(self):
        with pytest.raises(HTTPException) as exc:
            validate_file_size(_file_with_size(MAX_FILE_SIZE + 1), max_size=MAX_FILE_SIZE)
        assert exc.value.status_code == 413

    def test_at_limit_passes(self):
        # size == max_size : autorisé (strictement supérieur seulement rejeté)
        validate_file_size(_file_with_size(MAX_FILE_SIZE), max_size=MAX_FILE_SIZE)

    def test_size_none_fallback_computes_from_stream(self):
        # .size absent -> taille déduite via seek/tell sur le flux sous-jacent
        big = _FileWithoutSize(b"x" * 50)
        with pytest.raises(HTTPException) as exc:
            validate_file_size(big, max_size=10)
        assert exc.value.status_code == 413

    def test_size_none_fallback_under_limit_passes(self):
        small = _FileWithoutSize(b"x" * 5)
        validate_file_size(small, max_size=10)

    def test_undeterminable_size_passes(self):
        # Ni .size ni .file exploitable -> on laisse passer (pas de faux positif)
        broken = types.SimpleNamespace()  # pas de .size, pas de .file
        validate_file_size(broken, max_size=10)

    def test_custom_max_size(self):
        with pytest.raises(HTTPException):
            validate_file_size(_file_with_size(200), max_size=100)


class TestConstants:
    def test_pdf_mime_allowed(self):
        assert "application/pdf" in ALLOWED_MIME_TYPES

    def test_common_extensions_allowed(self):
        for ext in (".pdf", ".txt", ".md", ".csv", ".docx", ".xlsx"):
            assert ext in ALLOWED_EXTENSIONS

    def test_executable_not_allowed(self):
        assert ".exe" not in ALLOWED_EXTENSIONS
        assert "application/x-msdownload" not in ALLOWED_MIME_TYPES

    def test_size_limits(self):
        assert MAX_FILE_SIZE == 100 * 1024 * 1024
        assert MAX_TEXT_SIZE == 10 * 1024 * 1024
        assert MAX_TEXT_SIZE < MAX_FILE_SIZE


def test_upload_validation_error_is_exception():
    assert issubclass(UploadValidationError, Exception)
