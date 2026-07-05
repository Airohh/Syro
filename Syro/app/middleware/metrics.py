"""Middleware pour métriques Prometheus."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Créer des stubs pour éviter les erreurs si prometheus_client n'est pas installé
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, *args, **kwargs):
            pass

    def generate_latest():
        return b"# Prometheus client not installed\n"

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

# Métriques HTTP
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Métriques RAG
rag_queries_total = Counter(
    "rag_queries_total", "Total number of RAG queries", ["domain", "status"]
)

rag_query_duration_seconds = Histogram(
    "rag_query_duration_seconds",
    "RAG query duration in seconds",
    ["domain"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

rag_tokens_total = Counter(
    "rag_tokens_total",
    "Total tokens used in RAG queries",
    ["domain", "type"],  # type: prompt, completion, total
)

rag_sources_retrieved = Histogram(
    "rag_sources_retrieved",
    "Number of sources retrieved per query",
    ["domain"],
    buckets=[1, 3, 5, 10, 20, 50],
)

# Métriques ingestion
document_ingestions_total = Counter(
    "document_ingestions_total",
    "Total number of document ingestions",
    ["domain", "status"],  # status: queued, processing, complete, failed
)

document_ingestion_duration_seconds = Histogram(
    "document_ingestion_duration_seconds",
    "Document ingestion duration in seconds",
    ["domain"],
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

document_chunks_total = Counter(
    "document_chunks_total", "Total number of document chunks created", ["domain"]
)

# Métriques système
active_requests = Gauge("active_requests", "Number of active HTTP requests")

active_ingestions = Gauge(
    "active_ingestions", "Number of active document ingestions", ["domain"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware pour collecter les métriques HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not PROMETHEUS_AVAILABLE:
            return await call_next(request)

        # Normaliser le path (enlever les IDs pour éviter le cardinality explosion)
        endpoint = self._normalize_path(request.url.path)

        # Incrémenter les requêtes actives
        active_requests.inc()

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Enregistrer les métriques
            http_requests_total.labels(
                method=request.method, endpoint=endpoint, status_code=status_code
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=request.method, endpoint=endpoint, status_code=status_code
            ).observe(duration)

            return response

        except Exception:
            status_code = 500
            duration = time.time() - start_time

            http_requests_total.labels(
                method=request.method, endpoint=endpoint, status_code=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method, endpoint=endpoint, status_code=status_code
            ).observe(duration)

            raise

        finally:
            # Décrémenter les requêtes actives
            active_requests.dec()

    def _normalize_path(self, path: str) -> str:
        """
        Normaliser le path pour éviter le cardinality explosion.

        Exemples:
            /documents/123 -> /documents/{id}
            /domains/tech/chat/message -> /domains/{domain}/chat/message
        """
        import re

        # Remplacer les IDs numériques
        path = re.sub(r"/\d+", "/{id}", path)

        # Remplacer les UUIDs
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            path,
            flags=re.IGNORECASE,
        )

        return path


def get_metrics_response():
    """Générer la réponse Prometheus pour /metrics."""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not installed\n", CONTENT_TYPE_LATEST

    return generate_latest(), CONTENT_TYPE_LATEST
