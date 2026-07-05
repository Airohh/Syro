"""Chat service with enhanced RAG and citations."""

import sqlite3
import time
from typing import Any

from ..config import settings
from .rag import retrieve_chunks_with_metadata
from .llm import answer_from_context, answer_from_context_stream
from .domain_detector import detect_domain
from .multi_domain_rag import search_multi_domain
from .mlops_tracker import get_mlops_tracker
from .retrieval_filters import build_retrieval_scope
from .adaptive_performance import get_adaptive_manager
from .langfuse_tracer import log_generation, log_retrieval, rag_trace


def _sources_from_chunks(chunk_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
            "score": float(r.get("score", 0.0)),
            "metadata": r.get("metadata", {}) or {},
        }
        for r in chunk_results
    ]


def _filter_chunk_results(
    query: str, chunk_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not settings.enable_self_rag:
        return chunk_results
    from .self_rag import filter_relevant_chunks

    return filter_relevant_chunks(query, chunk_results)


def create_conversation_if_needed(
    db: sqlite3.Connection,
    organization_id: int,
    conversation_id: int | None,
    title: str | None = None,
) -> int:
    if conversation_id:
        return conversation_id
    cur = db.execute(
        "INSERT INTO conversations (organization_id, title) VALUES (?, ?)",
        (organization_id, title or "New conversation"),
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
        "INSERT INTO messages (conversation_id, sender_type, sender_id, content) VALUES (?, ?, ?, ?)",
        (conversation_id, sender_type, sender_id, content),
    )
    return cur.lastrowid


def load_conversation_history(
    db: sqlite3.Connection,
    conversation_id: int,
    limit: int = 6,
) -> list[str]:
    """Derniers tours user/assistant pour le retrieval et le prompt (T2.5)."""
    rows = db.execute(
        """
        SELECT sender_type, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (conversation_id, limit),
    ).fetchall()
    return [f"{row['sender_type']}: {row['content']}" for row in reversed(rows)]


def _get_detected_domains(
    query: str,
    auto_detect_domain: bool | None,
    forced_domain: str | None = None,
) -> tuple[list[str] | None, str]:
    """
    Determine which domains to use for a query.

    Priority:
    1. If forced_domain is provided, always use it (no auto-detect).
    2. Else, optionally auto-detect when current settings.domain == "general".
    3. Fallback to settings.domain.
    """
    if forced_domain:
        # Explicit domain passed by API (e.g. /domains/{domain}/chat)
        return None, forced_domain

    use_auto_detect = auto_detect_domain is True or (
        auto_detect_domain is None and settings.domain == "general"
    )

    if use_auto_detect:
        # detect_domain ne doit jamais faire échouer la requête : en cas de
        # pépin (dépendance manquante, entrée inattendue) on retombe sur le
        # domaine par défaut au lieu de remonter une 500.
        try:
            detected_domains = detect_domain(query)
        except Exception:  # pragma: no cover - garde défensive
            detected_domains = None
        primary_domain = detected_domains[0] if detected_domains else settings.domain
        return detected_domains, primary_domain

    return None, settings.domain


def build_answer(
    organization_id: int,
    query: str,
    filters: dict[str, Any] | None = None,
    include_sources: bool = True,
    auto_detect_domain: bool | None = None,
    domain: str | None = None,
    user_id: int | None = None,
    conversation_history: list[str] | None = None,
) -> tuple[str, int, list[dict[str, Any]]]:
    detected_domains, primary_domain = _get_detected_domains(
        query=query,
        auto_detect_domain=auto_detect_domain,
        forced_domain=domain,
    )
    scope = build_retrieval_scope(user_id, organization_id)
    multi_domain = bool(detected_domains and len(detected_domains) > 1)
    domain_to_use = (
        detected_domains[0] if multi_domain else (primary_domain or settings.domain)
    )

    with rag_trace(
        "build_answer",
        query=query,
        organization_id=organization_id,
        user_id=user_id,
        domain=domain_to_use,
        metadata={
            "multi_domain": multi_domain,
            "history_turns": len(conversation_history or []),
        },
    ) as trace:
        retrieval_t0 = time.time()
        if multi_domain:
            chunk_results = search_multi_domain(
                organization_id=organization_id,
                query=query,
                domains=detected_domains,
                allowed_document_ids=scope.allowed_document_ids,
                history=conversation_history,
            )
        else:
            chunk_results = retrieve_chunks_with_metadata(
                organization_id=organization_id,
                query=query,
                filters=filters,
                use_hybrid=True,
                domain=primary_domain,
                allowed_document_ids=scope.allowed_document_ids,
                history=conversation_history,
            )
        chunk_results = _filter_chunk_results(query, chunk_results)
        retrieval_ms = (time.time() - retrieval_t0) * 1000
        log_retrieval(
            trace,
            query=query,
            chunks=chunk_results,
            latency_ms=retrieval_ms,
            extra={
                "crag": settings.enable_crag,
                "self_rag": settings.enable_self_rag,
                "decomposition": settings.enable_query_decomposition,
                "semantic_cache": settings.enable_semantic_cache,
            },
        )

        context_chunks = [r["text"] for r in chunk_results]
        sources = (
            _sources_from_chunks(chunk_results)
            if (include_sources or multi_domain)
            else []
        )

        gen_t0 = time.time()
        try:
            answer, usage = answer_from_context(
                query,
                context_chunks,
                domain=domain_to_use,
                conversation_history=conversation_history,
            )
            log_generation(
                trace,
                query=query,
                answer=answer,
                num_context_chunks=len(context_chunks),
                latency_ms=(time.time() - gen_t0) * 1000,
            )
            response_time_ms = (time.time() - gen_t0) * 1000

            try:
                from ..middleware import (
                    rag_queries_total,
                    rag_query_duration_seconds,
                    rag_tokens_total,
                    rag_sources_retrieved,
                )

                rag_queries_total.labels(domain=domain_to_use, status="success").inc()
                rag_query_duration_seconds.labels(domain=domain_to_use).observe(
                    response_time_ms / 1000.0
                )
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    total_tokens = usage.get("total_tokens", 0)
                else:
                    total_tokens = usage if isinstance(usage, int) else 0
                    prompt_tokens = 0
                    completion_tokens = 0

                rag_tokens_total.labels(domain=domain_to_use, type="prompt").inc(
                    prompt_tokens
                )
                rag_tokens_total.labels(domain=domain_to_use, type="completion").inc(
                    completion_tokens
                )
                rag_tokens_total.labels(domain=domain_to_use, type="total").inc(
                    total_tokens
                )
                rag_sources_retrieved.labels(domain=domain_to_use).observe(len(sources))
            except ImportError:
                pass

            if settings.performance_mode == "adaptive":
                get_adaptive_manager().record_latency(response_time_ms)

            tracker = get_mlops_tracker()
            if tracker.enabled:
                avg_score = (
                    sum(s.get("score", 0.0) for s in sources) / max(len(sources), 1)
                    if sources
                    else 0.0
                )
                tracker.log_rag_query(
                    query=query,
                    organization_id=organization_id,
                    retrieval_method="hybrid",
                    num_sources=len(sources),
                    avg_source_score=avg_score,
                    response_time_ms=response_time_ms,
                    token_usage=usage,
                    domain=domain_to_use,
                    num_context_chunks=len(context_chunks),
                )

            return answer, usage, sources

        except Exception:
            response_time_ms = (time.time() - gen_t0) * 1000
            try:
                from ..middleware import rag_queries_total, rag_query_duration_seconds

                rag_queries_total.labels(domain=domain_to_use, status="error").inc()
                rag_query_duration_seconds.labels(domain=domain_to_use).observe(
                    response_time_ms / 1000.0
                )
            except ImportError:
                pass
            raise


def build_answer_stream(
    organization_id: int,
    query: str,
    filters: dict[str, Any] | None = None,
    auto_detect_domain: bool | None = None,
    domain: str | None = None,
    user_id: int | None = None,
    conversation_history: list[str] | None = None,
):
    detected_domains, primary_domain = _get_detected_domains(
        query=query,
        auto_detect_domain=auto_detect_domain,
        forced_domain=domain,
    )
    scope = build_retrieval_scope(user_id, organization_id)

    if detected_domains and len(detected_domains) > 1:
        chunk_results = search_multi_domain(
            organization_id=organization_id,
            query=query,
            domains=detected_domains,
            allowed_document_ids=scope.allowed_document_ids,
            history=conversation_history,
        )
        chunk_results = _filter_chunk_results(query, chunk_results)
        context_chunks = [r["text"] for r in chunk_results]
        domain_to_use = detected_domains[0]
    else:
        chunk_results = retrieve_chunks_with_metadata(
            organization_id=organization_id,
            query=query,
            filters=filters,
            use_hybrid=True,
            domain=primary_domain,
            allowed_document_ids=scope.allowed_document_ids,
            history=conversation_history,
        )
        chunk_results = _filter_chunk_results(query, chunk_results)
        context_chunks = [r["text"] for r in chunk_results]
        domain_to_use = primary_domain

    for chunk in answer_from_context_stream(
        query,
        context_chunks,
        domain=domain_to_use,
        conversation_history=conversation_history,
    ):
        yield chunk
