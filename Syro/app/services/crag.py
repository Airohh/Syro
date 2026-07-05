"""CRAG — Corrective Retrieval-Augmented Generation (T3.1).

Évalue la pertinence des chunks retrievés ; si faible, relance un retrieval
élargi (top_k × N + reformulations forcées).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from ..config import settings
from .hybrid_search import hybrid_search
from .query_rewriter import expand_queries
from .retrieval_scoring import normalize_rrf_score

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)

_TERM_RE = re.compile(r"\b\w+\b", re.UNICODE)


def _query_terms(query: str) -> set[str]:
    return {t for t in _TERM_RE.findall(query.lower()) if len(t) > 2}


def lexical_overlap(query: str, chunk_texts: list[str]) -> float:
    """Fraction des termes significatifs de la question présents dans les chunks."""
    terms = _query_terms(query)
    if not terms:
        return 0.0
    found: set[str] = set()
    for text in chunk_texts:
        found |= _query_terms(text)
    return len(terms & found) / len(terms)


def top_retrieval_strength(chunks: list[dict[str, Any]]) -> float:
    """Normalise le score RRF du meilleur chunk (0–1)."""
    if not chunks:
        return 0.0
    return normalize_rrf_score(chunks[0].get("score", 0.0))


def assess_retrieval_quality(
    query: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Évaluateur léger sans LLM : overlap lexical + force du top score RRF.

    Retourne verdict (correct | ambiguous | incorrect), score combiné [0–1].
    """
    if not chunks:
        return {"verdict": "incorrect", "score": 0.0, "overlap": 0.0, "strength": 0.0}

    overlap = lexical_overlap(query, [c["text"] for c in chunks[:3]])
    strength = top_retrieval_strength(chunks)
    score = 0.4 * strength + 0.6 * overlap

    if score < settings.crag_incorrect_threshold:
        verdict = "incorrect"
    elif score < settings.crag_retry_threshold:
        verdict = "ambiguous"
    else:
        verdict = "correct"

    return {
        "verdict": verdict,
        "score": round(score, 4),
        "overlap": round(overlap, 4),
        "strength": round(strength, 4),
    }


def _merge_chunk_lists(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    """Fusionne deux listes par chunk_id en gardant le meilleur score."""
    by_id: dict[str, dict[str, Any]] = {}
    for chunk in primary + secondary:
        cid = str(chunk["chunk_id"])
        existing = by_id.get(cid)
        if existing is None or float(chunk.get("score", 0)) > float(existing.get("score", 0)):
            by_id[cid] = chunk
    merged = sorted(by_id.values(), key=lambda c: float(c.get("score", 0)), reverse=True)
    return merged[:top_k]


def retrieve_with_crag(
    organization_id: int,
    query: str,
    top_k: int | None = None,
    filters: dict[str, Any] | None = None,
    domain: str | None = None,
    history: list[str] | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    query_embedding: np.ndarray | None = None,
) -> list[dict[str, Any]]:
    """Retrieval hybride avec passe corrective optionnelle si pertinence faible."""
    if top_k is None:
        top_k = settings.rerank_top_k

    results = hybrid_search(
        organization_id=organization_id,
        query=query,
        top_k=top_k,
        filters=filters,
        domain=domain,
        history=history,
        allowed_document_ids=allowed_document_ids,
        query_embedding=query_embedding,
    )
    assessment = assess_retrieval_quality(query, results)

    if assessment["verdict"] == "correct":
        return results

    retry_top_k = min(
        top_k * settings.crag_retry_top_k_multiplier,
        settings.retrieval_top_k * 2,
    )
    retry_queries = expand_queries(query, history=history, force=True)

    logger.info(
        "CRAG corrective retrieval (verdict=%s, score=%.3f, retry_top_k=%d, variants=%d)",
        assessment["verdict"],
        assessment["score"],
        retry_top_k,
        len(retry_queries),
    )

    retry_results = hybrid_search(
        organization_id=organization_id,
        query=query,
        top_k=retry_top_k,
        filters=filters,
        domain=domain,
        history=history,
        allowed_document_ids=allowed_document_ids,
        queries=retry_queries,
    )
    retry_assessment = assess_retrieval_quality(query, retry_results)

    if retry_assessment["score"] > assessment["score"]:
        return retry_results[:top_k]

    merged = _merge_chunk_lists(results, retry_results, top_k)
    return merged if merged else results
