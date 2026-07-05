"""Query decomposition multi-hop (T3.3).

Décompose les questions composées en sous-requêtes, retrieval parallèle,
fusion RRF globale et rerank optionnel.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from ..config import settings
from .hybrid_search import hybrid_search
from .reranker import reranker

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

_MULTI_QUESTION_RE = re.compile(r"\?\s+")


def _split_multi_question(query: str) -> list[str]:
    """Découpe « Q1? Q2? » en sous-questions distinctes."""
    if query.count("?") < 2:
        return [query]
    parts = [p.strip() for p in _MULTI_QUESTION_RE.split(query) if p.strip()]
    if len(parts) < 2:
        return [query]
    return [p if p.endswith("?") else f"{p}?" for p in parts]


def _split_semicolon_clauses(query: str) -> list[str]:
    """Découpe les clauses séparées par « ; »."""
    if ";" not in query:
        return [query]
    parts = [p.strip() for p in query.split(";") if len(p.strip()) >= 12]
    return parts if len(parts) >= 2 else [query]


def _llm_decompose(query: str, history: Sequence[str] | None) -> list[str]:
    """Sous-requêtes via LLM (fallback si heuristiques insuffisantes)."""
    from .llm import provider

    if not provider._chat_model:
        return []

    try:
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
    except ImportError:
        return []

    if not provider._chat_breaker.allow():
        return []

    history_block = ""
    if history:
        recent = list(history)[-3:]
        history_block = (
            "Contexte récent:\n" + "\n".join(f"- {h}" for h in recent) + "\n\n"
        )

    system = (
        "Tu décomposes une question complexe en 2 à 3 sous-questions autonomes "
        "pour une recherche documentaire. Une sous-question par ligne, sans numérotation."
    )
    user = f"{history_block}Question: {query}"

    try:
        response = provider._chat_model.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        text = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )
        provider._chat_breaker.record_success()
    except Exception as exc:
        provider._chat_breaker.record_failure()
        logger.warning("Query decomposition LLM failed: %s", exc)
        return []

    from .query_rewriter import _parse_rewrite_lines

    return _parse_rewrite_lines(text)


def decompose(query: str, history: Sequence[str] | None = None) -> list[str]:
    """Retourne la question originale ou une liste de sous-requêtes."""
    original = query.strip()
    if not original:
        return [query]
    if not settings.enable_query_decomposition:
        return [original]

    max_sub = max(2, settings.query_decomposition_max_subqueries)

    for splitter in (_split_multi_question, _split_semicolon_clauses):
        parts = splitter(original)
        if len(parts) >= 2:
            return parts[:max_sub]

    llm_parts = _llm_decompose(original, history)
    if len(llm_parts) >= 2:
        deduped = [original]
        seen = {original.lower()}
        for part in llm_parts:
            key = part.lower().strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(part)
        if len(deduped) >= 2:
            return deduped[:max_sub]

    return [original]


def fuse_rrf_lists(
    result_lists: list[list[dict[str, Any]]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Fusion RRF globale sur plusieurs listes de chunks."""
    rrf_k = settings.rrf_k
    chunk_map: dict[str, dict[str, Any]] = {}

    for results in result_lists:
        for rank, result in enumerate(results):
            chunk_id = str(result["chunk_id"])
            entry = chunk_map.get(chunk_id)
            if entry is None:
                entry = {
                    "chunk_id": result["chunk_id"],
                    "text": result["text"],
                    "metadata": dict(result.get("metadata") or {}),
                    "rrf_score": 0.0,
                }
                chunk_map[chunk_id] = entry
            entry["rrf_score"] += 1.0 / (rrf_k + rank)

    fused = [
        {
            "chunk_id": e["chunk_id"],
            "text": e["text"],
            "score": e["rrf_score"],
            "metadata": e["metadata"],
        }
        for e in chunk_map.values()
    ]
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]


def retrieve_decomposed(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    domain: str | None = None,
    history: list[str] | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    query_embedding: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    """Retrieval multi-hop : sous-requêtes parallèles + fusion RRF + rerank."""
    if top_k is None:
        top_k = settings.rerank_top_k

    subqueries = decompose(query, history=history)
    if len(subqueries) <= 1:
        from .crag import retrieve_with_crag

        if settings.enable_crag:
            return retrieve_with_crag(
                organization_id=organization_id,
                query=query,
                top_k=top_k,
                filters=filters,
                domain=domain,
                history=history,
                allowed_document_ids=allowed_document_ids,
                query_embedding=query_embedding,
            )
        return hybrid_search(
            organization_id=organization_id,
            query=query,
            top_k=top_k,
            filters=filters,
            domain=domain,
            history=history,
            allowed_document_ids=allowed_document_ids,
            query_embedding=query_embedding,
        )

    per_sub_k = min(settings.retrieval_top_k, max(top_k, 5))
    logger.info(
        "Query decomposition: %d subqueries for %r", len(subqueries), query[:80]
    )

    def _search_one(subquery: str) -> list[dict[str, Any]]:
        sub_embedding = query_embedding if subquery == query else None
        if settings.enable_crag:
            from .crag import retrieve_with_crag

            return retrieve_with_crag(
                organization_id=organization_id,
                query=subquery,
                top_k=per_sub_k,
                filters=filters,
                domain=domain,
                history=history,
                allowed_document_ids=allowed_document_ids,
                query_embedding=sub_embedding,
            )
        return hybrid_search(
            organization_id=organization_id,
            query=subquery,
            top_k=per_sub_k,
            filters=filters,
            domain=domain,
            history=history,
            allowed_document_ids=allowed_document_ids,
            query_embedding=sub_embedding,
        )

    with ThreadPoolExecutor(max_workers=min(4, len(subqueries))) as executor:
        result_lists = list(executor.map(_search_one, subqueries))

    fused = fuse_rrf_lists(result_lists, top_k=top_k * 2)

    if settings.enable_reranking and len(fused) > 1:
        try:
            reranked = reranker.rerank(query=query, passages=fused, top_k=top_k)
            for result in reranked:
                if "final_score" in result:
                    result["score"] = result["final_score"]
            return reranked
        except Exception:
            return fused[:top_k]

    return fused[:top_k]
