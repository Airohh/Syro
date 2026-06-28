"""Query rewriting / expansion avant retrieval (T2.1)."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from ..config import settings

logger = logging.getLogger(__name__)

_LINE_PREFIX = re.compile(r"^[\s\-•*\d.)]+")


def _parse_rewrite_lines(text: str) -> list[str]:
    """Extrait des variantes une réponse LLM (une reformulation par ligne)."""
    variants: list[str] = []
    for raw in text.splitlines():
        line = _LINE_PREFIX.sub("", raw).strip()
        if len(line) >= 3:
            variants.append(line)
    return variants


def _llm_rewrite_variants(query: str, history: Sequence[str] | None) -> list[str]:
    """Appelle le chat LLM pour produire 1–2 reformulations (sans l'originale)."""
    # Import local pour éviter les cycles et garder les tests légers.
    from .llm import provider

    if not provider._chat_model:
        return []

    try:
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
    except ImportError:
        return []

    if not provider._chat_breaker.allow():
        return []

    history_lines = ""
    if history:
        recent = list(history)[-3:]
        history_lines = "Contexte récent:\n" + "\n".join(f"- {h}" for h in recent) + "\n\n"

    system = (
        "Tu aides une recherche documentaire. Propose 1 à 2 reformulations courtes "
        "de la question (synonymes, termes techniques, formulation alternative). "
        "Une reformulation par ligne, sans numérotation ni explication."
    )
    user = f"{history_lines}Question: {query}"

    try:
        response = provider._chat_model.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        text = response.content if isinstance(response.content, str) else str(response.content)
        provider._chat_breaker.record_success()
        return _parse_rewrite_lines(text)
    except Exception as exc:
        provider._chat_breaker.record_failure()
        logger.warning("Query rewrite LLM failed, using original only: %s", exc)
        return []


def rewrite(query: str, history: Sequence[str] | None = None, *, force: bool = False) -> list[str]:
    """
    Retourne la question originale + variantes pour le retrieval.

    Toujours inclut `query` en première position. Déduplique (casse/espaces).
    `force=True` ignore enable_query_rewriting (passe corrective CRAG).
    """
    original = query.strip()
    if not original:
        return [query]

    if not settings.enable_query_rewriting and not force:
        return [original]

    extra = _llm_rewrite_variants(original, history)
    max_extra = max(0, settings.query_rewrite_max_variants)
    seen = {original.lower()}
    result = [original]

    for variant in extra:
        if len(result) - 1 >= max_extra:
            break
        key = variant.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(variant)

    return result


def expand_queries(
    query: str,
    history: Sequence[str] | None = None,
    *,
    force: bool = False,
) -> list[str]:
    """Alias explicite pour hybrid_search (originale + reformulations)."""
    return rewrite(query, history=history, force=force)
