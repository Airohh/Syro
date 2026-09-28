"""Garde-fous sécurité : secret JWT + CORS wildcard/credentials."""

from app.config import Settings, _DEFAULT_SECRET_KEY
from app.main import resolve_cors_settings


class TestSecretKey:
    def test_generated_when_missing_and_persisted(self, tmp_path):
        s = Settings(data_dir=tmp_path, secret_key=_DEFAULT_SECRET_KEY)
        s.ensure_secret_key()
        assert s.secret_key != _DEFAULT_SECRET_KEY
        assert len(s.secret_key) >= 32

        # Un 2e process (autre worker uvicorn) relit le même secret.
        other = Settings(data_dir=tmp_path, secret_key=_DEFAULT_SECRET_KEY)
        other.ensure_secret_key()
        assert other.secret_key == s.secret_key
        assert (tmp_path / ".secret_key").stat().st_mode & 0o077 == 0

    def test_explicit_secret_kept(self, tmp_path):
        s = Settings(data_dir=tmp_path, secret_key="a-strong-random-secret")
        s.ensure_secret_key()
        assert s.secret_key == "a-strong-random-secret"
        assert not (tmp_path / ".secret_key").exists()

    def test_debug_off_by_default(self):
        assert Settings.model_fields["debug"].default is False


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
