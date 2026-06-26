"""Tests unitaires pour le circuit breaker (module pur, sans dépendances)."""

import pytest

from app.services.circuit_breaker import CircuitBreaker

class TestCircuitBreaker:
    def test_closed_by_default(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)
        assert cb.allow()
        assert not cb.is_open

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.allow()
        assert not cb.is_open

    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open
        assert not cb.allow()

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, reset_timeout=30.0)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        cb.record_failure()
        assert cb.allow()
        assert not cb.is_open

    def test_half_open_after_reset_timeout(self, monkeypatch):
        import app.services.circuit_breaker as cb_module

        now = [1000.0]
        monkeypatch.setattr(cb_module.time, "monotonic", lambda: now[0])

        cb = CircuitBreaker(failure_threshold=2, reset_timeout=30.0)
        cb.record_failure()
        cb.record_failure()
        assert not cb.allow()

        # Avant la fin du repos : toujours fermé au trafic
        now[0] += 29.0
        assert not cb.allow()

        # Après le repos : un seul essai passe (half-open)
        now[0] += 2.0
        assert cb.allow()
        assert not cb.allow()  # deuxième appel bloqué pendant l'essai

    def test_half_open_success_closes(self, monkeypatch):
        import app.services.circuit_breaker as cb_module

        now = [1000.0]
        monkeypatch.setattr(cb_module.time, "monotonic", lambda: now[0])

        cb = CircuitBreaker(failure_threshold=2, reset_timeout=30.0)
        cb.record_failure()
        cb.record_failure()
        now[0] += 31.0
        assert cb.allow()
        cb.record_success()
        assert not cb.is_open
        assert cb.allow()

    def test_half_open_failure_reopens(self, monkeypatch):
        import app.services.circuit_breaker as cb_module

        now = [1000.0]
        monkeypatch.setattr(cb_module.time, "monotonic", lambda: now[0])

        cb = CircuitBreaker(failure_threshold=2, reset_timeout=30.0)
        cb.record_failure()
        cb.record_failure()
        now[0] += 31.0
        assert cb.allow()
        cb.record_failure()  # l'essai échoue → réouverture immédiate
        assert cb.is_open
        assert not cb.allow()

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError):
            CircuitBreaker(failure_threshold=0)
