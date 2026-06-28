"""Tracing RAG via Langfuse (T1.3).

No-op si désactivé ou SDK indisponible. Instrumente retrieval + génération
depuis build_answer.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from ..config import settings

logger = logging.getLogger(__name__)

_client: Any = None
_init_attempted = False


class _NoOpHandle:
    """Substitut quand Langfuse est off ou non installé."""

    id: str | None = None

    def span(self, **kwargs: Any) -> _NoOpHandle:
        return self

    def generation(self, **kwargs: Any) -> _NoOpHandle:
        return self

    def event(self, **kwargs: Any) -> None:
        return None

    def update(self, **kwargs: Any) -> None:
        return None

    def end(self, **kwargs: Any) -> None:
        return None


def _get_client() -> Any | None:
    global _client, _init_attempted
    if _init_attempted:
        return _client
    _init_attempted = True

    if not settings.langfuse_enabled:
        return None
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        logger.warning("Langfuse enabled but keys missing — tracing disabled")
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except ImportError:
        logger.warning("langfuse package not installed — tracing disabled")
        _client = None
    except Exception as exc:
        logger.warning("Langfuse init failed: %s", exc)
        _client = None
    return _client


def flush() -> None:
    client = _get_client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:
            logger.debug("Langfuse flush failed: %s", exc)


@contextmanager
def rag_trace(
    name: str,
    *,
    query: str,
    organization_id: int,
    user_id: int | None = None,
    domain: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any]:
    """Trace racine d'une requête RAG (chat)."""
    client = _get_client()
    if client is None:
        yield _NoOpHandle()
        return

    meta = dict(metadata or {})
    if domain:
        meta["domain"] = domain
    meta["organization_id"] = organization_id

    trace = client.trace(
        name=name,
        user_id=str(user_id) if user_id is not None else None,
        input={"query": query},
        metadata=meta,
        tags=["rag", "syro"],
    )
    try:
        yield trace
    finally:
        flush()


def log_retrieval(
    trace: Any,
    *,
    query: str,
    chunks: list[dict[str, Any]],
    latency_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Span retrieval : candidats + scores."""
    if isinstance(trace, _NoOpHandle):
        return

    top = [
        {
            "chunk_id": str(c.get("chunk_id")),
            "score": float(c.get("score", 0)),
            "text_preview": (c.get("text") or "")[:120],
        }
        for c in chunks[:8]
    ]
    output: dict[str, Any] = {
        "num_chunks": len(chunks),
        "top_chunks": top,
    }
    if latency_ms is not None:
        output["latency_ms"] = round(latency_ms, 2)
    if extra:
        output.update(extra)

    try:
        span = trace.span(
            name="retrieval",
            input={"query": query},
            output=output,
            metadata=extra or {},
        )
        span.end()
    except Exception as exc:
        logger.debug("Langfuse retrieval span failed: %s", exc)


def log_generation(
    trace: Any,
    *,
    query: str,
    answer: str,
    num_context_chunks: int,
    latency_ms: float | None = None,
) -> None:
    """Span génération LLM."""
    if isinstance(trace, _NoOpHandle):
        return

    output: dict[str, Any] = {
        "answer_preview": answer[:500],
        "num_context_chunks": num_context_chunks,
    }
    if latency_ms is not None:
        output["latency_ms"] = round(latency_ms, 2)

    try:
        gen = trace.generation(
            name="answer",
            model=settings.chat_model,
            input={"query": query},
            output=output,
        )
        gen.end()
        trace.update(output={"answer_length": len(answer)})
    except Exception as exc:
        logger.debug("Langfuse generation span failed: %s", exc)


def log_event(trace: Any, name: str, metadata: dict[str, Any]) -> None:
    if isinstance(trace, _NoOpHandle):
        return
    try:
        trace.event(name=name, metadata=metadata)
    except Exception as exc:
        logger.debug("Langfuse event failed: %s", exc)
