"""Garde-fous sécurité : secret de prod + CORS wildcard/credentials."""

import pytest

from app.config import Settings, _DEFAULT_SECRET_KEY
from app.main import resolve_cors_settings


class TestProductionSecrets:
    def test_default_secret_rejected_in_prod(self):
        s = Settings()
        s.debug = False
        s.secret_key = _DEFAULT_SECRET_KEY
        with pytest.raises(RuntimeError):
            s.validate_production_secrets()

    def test_custom_secret_ok_in_prod(self):
        s = Settings()
        s.debug = False
        s.secret_key = "a-strong-random-secret"
        s.validate_production_secrets()  # ne lève pas

    def test_default_secret_ok_in_debug(self):
        s = Settings()
        s.debug = True
        s.secret_key = _DEFAULT_SECRET_KEY
        s.validate_production_secrets()  # debug → toléré


class TestCorsSettings:
    def test_wildcard_forces_credentials_off(self):
        origins, creds = resolve_cors_settings("*", True)
        assert origins == ["*"]
        assert creds is False

    def test_explicit_origins_keep_credentials(self):
        origins, creds = resolve_cors_settings(
            "http://localhost:5173, http://127.0.0.1:5173", True
        )
        assert origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
        assert creds is True

    def test_wildcard_among_others_still_off(self):
        _, creds = resolve_cors_settings("http://a.b, *", True)
        assert creds is False
