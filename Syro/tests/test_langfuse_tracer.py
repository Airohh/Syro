"""Tests Langfuse tracer (T1.3) — no-op par défaut, sans SDK live."""

from unittest.mock import MagicMock, patch

from app.services.langfuse_tracer import (
    _NoOpHandle,
    log_generation,
    log_retrieval,
    rag_trace,
)


class TestRagTraceNoOp:
    @patch("app.services.langfuse_tracer.settings")
    def test_disabled_yields_noop(self, mock_settings):
        mock_settings.langfuse_enabled = False

        with rag_trace("t", query="q", organization_id=1) as trace:
            assert isinstance(trace, _NoOpHandle)

    @patch("app.services.langfuse_tracer.settings")
    def test_log_retrieval_noop_safe(self, mock_settings):
        mock_settings.langfuse_enabled = False
        log_retrieval(_NoOpHandle(), query="q", chunks=[], latency_ms=1.0)

    @patch("app.services.langfuse_tracer.settings")
    def test_log_generation_noop_safe(self, mock_settings):
        mock_settings.langfuse_enabled = False
        log_generation(
            _NoOpHandle(), query="q", answer="a", num_context_chunks=0, latency_ms=1.0
        )


class TestRagTraceWithClient:
    @patch("app.services.langfuse_tracer._get_client")
    @patch("app.services.langfuse_tracer.settings")
    def test_trace_creates_spans(self, mock_settings, mock_get_client):
        mock_settings.langfuse_enabled = True
        mock_settings.langfuse_public_key = "pk"
        mock_settings.langfuse_secret_key = "sk"
        mock_settings.langfuse_host = "http://localhost:3000"
        mock_settings.chat_model = "test-model"

        mock_trace = MagicMock()
        mock_span = MagicMock()
        mock_trace.span.return_value = mock_span
        mock_gen = MagicMock()
        mock_trace.generation.return_value = mock_gen

        mock_client = MagicMock()
        mock_client.trace.return_value = mock_trace
        mock_get_client.return_value = mock_client

        chunks = [{"chunk_id": "1", "text": "kubernetes pods", "score": 0.04}]
        with rag_trace("build_answer", query="q", organization_id=1, user_id=2) as trace:
            log_retrieval(trace, query="q", chunks=chunks, latency_ms=12.5)
            log_generation(
                trace, query="q", answer="réponse", num_context_chunks=1, latency_ms=50.0
            )

        mock_client.trace.assert_called_once()
        mock_trace.span.assert_called_once()
        mock_trace.generation.assert_called_once()
        mock_client.flush.assert_called()
