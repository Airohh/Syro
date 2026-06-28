"""Circuit breaker minimal pour les appels externes (LLM, embeddings).

Sans breaker, un backend LLM down fait payer le timeout complet (jusqu'à
LLM_TIMEOUT secondes) à CHAQUE requête utilisateur. Le breaker s'ouvre après
N échecs consécutifs et fait échouer immédiatement les appels suivants,
jusqu'à une période de repos où un appel d'essai est laissé passer (half-open).
"""

from __future__ import annotations

import threading
import time

class CircuitBreaker:
    """Breaker thread-safe à trois états implicites : closed / open / half-open.

    - closed : tout passe, les échecs consécutifs sont comptés.
    - open : `allow()` renvoie False pendant `reset_timeout` secondes.
    - half-open : après le timeout, UN appel d'essai passe ; succès → closed,
      échec → open pour un nouveau cycle.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open_trial_in_flight = False
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._opened_at is not None

    def allow(self) -> bool:
        """True si l'appel peut être tenté maintenant."""
        with self._lock:
            if self._opened_at is None:
                return True
            if time.monotonic() - self._opened_at < self.reset_timeout:
                return False
            # Période de repos écoulée : un seul appel d'essai à la fois.
            if self._half_open_trial_in_flight:
                return False
            self._half_open_trial_in_flight = True
            return True

    def record_success(self) -> None:
        with self._lock:
            self._consecutive_failures = 0
            self._opened_at = None
            self._half_open_trial_in_flight = False

    def record_failure(self) -> None:
        with self._lock:
            self._consecutive_failures += 1
            self._half_open_trial_in_flight = False
            if self._consecutive_failures >= self.failure_threshold:
                self._opened_at = time.monotonic()
