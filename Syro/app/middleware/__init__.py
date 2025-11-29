"""Middlewares pour observabilité."""

from .logging import (
    setup_logging,
    CorrelationIDMiddleware,
    get_logger,
)
from .metrics import (
    MetricsMiddleware,
    get_metrics_response,
    http_requests_total,
    http_request_duration_seconds,
    rag_queries_total,
    rag_query_duration_seconds,
    rag_tokens_total,
    rag_sources_retrieved,
    document_ingestions_total,
    document_ingestion_duration_seconds,
    document_chunks_total,
    active_requests,
    active_ingestions,
)
from .tracing import (
    setup_tracing,
    get_tracer,
)

__all__ = [
    "setup_logging",
    "CorrelationIDMiddleware",
    "get_logger",
    "MetricsMiddleware",
    "get_metrics_response",
    "http_requests_total",
    "http_request_duration_seconds",
    "rag_queries_total",
    "rag_query_duration_seconds",
    "rag_tokens_total",
    "rag_sources_retrieved",
    "document_ingestions_total",
    "document_ingestion_duration_seconds",
    "document_chunks_total",
    "active_requests",
    "active_ingestions",
    "setup_tracing",
    "get_tracer",
]

