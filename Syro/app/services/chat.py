"""Service de chat RAG : conversation → retrieval → génération → sources."""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from ..config import settings
from ..domains import normalize_domain
from .domain_detector import detect_domain
from .langfuse_tracer import log_generation, log_retrieval, rag_trace
from .llm import answer_from_context, answer_from_context_stream
from .rag import retrieve_chunks_with_metadata
from .retrieval_filters import build_retrieval_scope

logger = logging.getLogger(__name__)

NOT_FOUND_ANSWER = "Je ne trouve pas cette information dans vos documents."
HISTORY_TURNS = 6


class ConversationNotFound(LookupError):
    pass


# --------------------------------------------------------------------------
# Conversations
# --------------------------------------------------------------------------
def get_or_create_conversation(
    db: sqlite3.Connection,
    organization_id: int,
    user_id: int,
    conversation_id: int | None,
    title: str | None = None,
) -> int:
    """Conversation existante APPARTENANT à l'utilisateur, ou nouvelle.

    Vérifier l'appartenance empêche de lire (via le prompt) ou d'écrire dans
    la conversation d'un autre utilisateur / d'une autre organisation.
    """
    if conversation_id is not None:
        row = db.execute(
            "SELECT id FROM conversations WHERE id = ? AND organization_id = ? "
            "AND (user_id = ? OR user_id IS NULL)",
            (conversation_id, organization_id, user_id),
        ).fetchone()
        if row is None:
            raise ConversationNotFound(conversation_id)
        return conversation_id
    cur = db.execute(
        "INSERT INTO conversations (organization_id, user_id, title) VALUES (?, ?, ?)",
        (organization_id, user_id, (title or "Nouvelle conversation")[:80]),
    )
    return cur.lastrowid


def store_message(
    db: sqlite3.Connection,
    conversation_id: int,
    sender_type: str,
    content: str,
    sender_id: int | None,
) -> int:
    cur = db.execute(
        "INSERT INTO messages (conversation_id, sender_type, sender_id, content) "
        "VALUES (?, ?, ?, ?)",
        (conversation_id, sender_type, sender_id, content),
    )
    return cur.lastrowid


def load_conversation_history(
    db: sqlite3.Connection,
    conversation_id: int,
    limit: int = HISTORY_TURNS,
) -> list[dict[str, str]]:
    """Derniers messages, du plus ancien au plus récent : [{role, content}]."""
    rows = db.execute(
        "SELECT sender_type, content FROM messages WHERE conversation_id = ? "
        "ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    ).fetchall()
    return [
        {
            "role": "user" if r["sender_type"] == "user" else "assistant",
            "content": r["content"],
        }
        for r in reversed(rows)
    ]


def charge_usage(
    db: sqlite3.Connection, organization_id: int, user_id: int, usage: int
) -> None:
    db.execute(
        "INSERT INTO usage_events (organization_id, user_id, event_type, amount) "
        "VALUES (?, ?, 'chat_completion', ?)",
        (organization_id, user_id, usage),
    )
    db.execute(
        "UPDATE organizations SET credit_balance = MAX(credit_balance - ?, 0) WHERE id = ?",
        (usage, organization_id),
    )


# --------------------------------------------------------------------------
# RAG
# --------------------------------------------------------------------------
@dataclass
class RetrievalResult:
    chunks: list[dict[str, Any]]
    domain: str | None  # filtre appliqué (None = tous les documents)
    persona: str  # domaine utilisé pour la persona du LLM
    latency_ms: float
    sources: list[dict[str, Any]] = field(default_factory=list)


def _history_strings(history: list[dict[str, str]] | None) -> list[str]:
    return [f"{t['role']}: {t['content']}" for t in history or []]


def format_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sources renvoyées à l'UI : numérotées comme dans le prompt ([Source N])."""
    sources = []
    for i, chunk in enumerate(chunks, start=1):
        text = chunk["text"]
        meta = chunk.get("metadata") or {}
        sources.append(
            {
                "text": text if len(text) <= 300 else text[:300] + "…",
                "score": round(float(chunk.get("score", 0.0)), 4),
                "metadata": {
                    "source": i,
                    "filename": meta.get("filename"),
                    "document_id": meta.get("document_id"),
                    "domain": meta.get("domain"),
                    "header": meta.get("header"),
                    "chunk_index": meta.get("chunk_index"),
                    "rerank_score": chunk.get("rerank_score"),
                },
            }
        )
    return sources


def retrieve(
    organization_id: int,
    query: str,
    user_id: int | None,
    domain: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> RetrievalResult:
    """Domaine explicite → filtre + persona. Sinon : tous les documents,
    persona devinée par mots-clés (sans effet sur le retrieval)."""
    domain = normalize_domain(domain)
    persona = domain or detect_domain(query)
    scope = build_retrieval_scope(user_id, organization_id)

    t0 = time.time()
    chunks = retrieve_chunks_with_metadata(
        organization_id=organization_id,
        query=query,
        domain=domain,
        allowed_document_ids=scope.allowed_document_ids,
        history=_history_strings(history),
    )
    if settings.enable_self_rag:
        from .self_rag import filter_relevant_chunks

        chunks = filter_relevant_chunks(query, chunks)
    latency_ms = (time.time() - t0) * 1000
    return RetrievalResult(
        chunks=chunks,
        domain=domain,
        persona=persona,
        latency_ms=latency_ms,
        sources=format_sources(chunks),
    )


def _record_metrics(
    persona: str, status: str, seconds: float, usage: int, n: int
) -> None:
    try:
        from ..middleware import (
            rag_queries_total,
            rag_query_duration_seconds,
            rag_sources_retrieved,
            rag_tokens_total,
        )

        rag_queries_total.labels(domain=persona, status=status).inc()
        rag_query_duration_seconds.labels(domain=persona).observe(seconds)
        rag_tokens_total.labels(domain=persona, type="total").inc(usage)
        rag_sources_retrieved.labels(domain=persona).observe(n)
    except Exception:  # les métriques ne doivent jamais casser une réponse
        pass


def build_answer(
    organization_id: int,
    query: str,
    user_id: int | None = None,
    domain: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, int, list[dict[str, Any]]]:
    """Réponse complète : (texte, tokens, sources).

    Lève llm.LLMUnavailableError si le LLM est indisponible.
    """
    t0 = time.time()
    with rag_trace(
        "build_answer",
        query=query,
        organization_id=organization_id,
        user_id=user_id,
        domain=domain,
        metadata={"history_turns": len(conversation_history or [])},
    ) as trace:
        result = retrieve(organization_id, query, user_id, domain, conversation_history)
        log_retrieval(
            trace, query=query, chunks=result.chunks, latency_ms=result.latency_ms
        )

        if not result.chunks:
            # Rien de pertinent : réponse d'abstention sans appeler le LLM.
            _record_metrics(result.persona, "no_context", time.time() - t0, 0, 0)
            return NOT_FOUND_ANSWER, 0, []

        gen_t0 = time.time()
        try:
            answer, usage = answer_from_context(
                query,
                result.chunks,
                domain=result.persona,
                conversation_history=conversation_history,
            )
        except Exception:
            _record_metrics(
                result.persona, "error", time.time() - t0, 0, len(result.chunks)
            )
            raise
        log_generation(
            trace,
            query=query,
            answer=answer,
            num_context_chunks=len(result.chunks),
            latency_ms=(time.time() - gen_t0) * 1000,
        )

    _record_metrics(
        result.persona, "success", time.time() - t0, usage, len(result.chunks)
    )
    _track_mlflow(organization_id, query, result, usage, (time.time() - t0) * 1000)
    return answer, usage, result.sources


def build_answer_stream(
    organization_id: int,
    query: str,
    user_id: int | None = None,
    domain: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, Any]], Iterator[str]]:
    """(sources, générateur de fragments). Les sources sont connues avant le 1er token."""
    result = retrieve(organization_id, query, user_id, domain, conversation_history)
    if not result.chunks:
        return [], iter([NOT_FOUND_ANSWER])
    stream = answer_from_context_stream(
        query,
        result.chunks,
        domain=result.persona,
        conversation_history=conversation_history,
    )
    return result.sources, stream


def _track_mlflow(
    organization_id: int,
    query: str,
    result: RetrievalResult,
    usage: int,
    response_time_ms: float,
) -> None:
    try:
        from .mlops_tracker import get_mlops_tracker

        tracker = get_mlops_tracker()
        if not tracker.enabled:
            return
        scores = [s["score"] for s in result.sources]
        tracker.log_rag_query(
            query=query,
            organization_id=organization_id,
            retrieval_method="hybrid",
            num_sources=len(scores),
            avg_source_score=sum(scores) / len(scores) if scores else 0.0,
            response_time_ms=response_time_ms,
            token_usage=usage,
            domain=result.persona,
            num_context_chunks=len(result.chunks),
        )
    except Exception as exc:
        logger.debug("MLflow tracking skipped: %s", exc)
