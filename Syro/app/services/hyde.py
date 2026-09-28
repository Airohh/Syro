"""HyDE — Hypothetical Document Embeddings (T2.2).

Génère un passage hypothétique via LLM, l'embed, et l'utilise comme vecteur
de recherche additionnel (BM25 reste sur la question originale).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

import numpy as np

from ..config import settings

logger = logging.getLogger(__name__)


def generate_hypothetical_passage(
    query: str,
    history: Sequence[str] | None = None,
) -> str:
    """Produit un court passage plausible répondant à la question ('' si échec)."""
    from .llm import complete

    history_block = ""
    if history:
        recent = list(history)[-3:]
        history_block = (
            "Contexte récent:\n" + "\n".join(f"- {h}" for h in recent) + "\n\n"
        )
    return complete(
        "Tu rédiges un court extrait de document technique (3–6 phrases) qui "
        "répondrait plausiblement à la question, comme s'il venait d'une base "
        "de connaissances. Pas de méta-commentaire, pas de « selon le contexte ».",
        f"{history_block}Question: {query}",
    )


def get_hyde_embedding_vector(
    query: str,
    history: Sequence[str] | None = None,
) -> np.ndarray | None:
    """Embedding du passage hypothétique, ou None si HyDE désactivé / échec."""
    if not settings.enable_hyde:
        return None

    passage = generate_hypothetical_passage(query, history=history)
    if not passage:
        return None

    from .llm import get_document_embeddings

    try:
        # Le passage hypothétique est comparé à des passages : préfixe « document ».
        return get_document_embeddings([passage])[0]
    except Exception as exc:
        logger.warning("HyDE embedding failed: %s", exc)
        return None
