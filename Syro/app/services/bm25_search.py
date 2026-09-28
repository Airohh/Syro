"""Recherche lexicale BM25 (index en mémoire par organisation)."""

from __future__ import annotations

import re
import threading
import unicodedata
from typing import Any

from rank_bm25 import BM25Okapi

from ..db import db_session
from .vector_store import domain_filter_value

# Mots vides FR + EN : sans eux, « le », « de », « the » dominent les scores.
_STOPWORDS = frozenset(
    """
    a au aux avec ce ces c cet cette d dans de des du elle en et eux il ils je j
    l la le les leur lui ma mais me meme mes moi mon n ne nos notre nous on ou
    par pas pour qu que qui s sa se ses son sur t ta te tes toi ton tu un une
    vos votre vous y est sont etre avoir fait comme plus quel quelle quels
    quelles quoi comment pourquoi dont entre
    an and are as at be by for from how in is it of on or that the this to
    what when where which who why with
    """.split()
)
_TOKEN_RE = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Minuscules, sans accents, sans mots vides (« Évaluer » → « evaluer »)."""
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return [t for t in _TOKEN_RE.findall(folded) if t not in _STOPWORDS and len(t) > 1]


class BM25Search:
    def __init__(self) -> None:
        self._indexes: dict[int, tuple[BM25Okapi | None, list[dict[str, Any]]]] = {}
        self._fingerprints: dict[int, tuple[int, int]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def content_fingerprint(organization_id: int) -> tuple[int, int]:
        """(nombre, id max) des chunks actifs de l'org.

        L'index vit en mémoire par processus : l'ingestion faite par le worker
        Celery ne l'invalide pas directement. Cette empreinte (1 requête SQL)
        détecte les changements faits par un autre processus.
        """
        with db_session() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n, COALESCE(MAX(dc.id), 0) AS max_id
                FROM doc_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.organization_id = ? AND d.status = 'active'
                """,
                (organization_id,),
            ).fetchone()
        return (row["n"], row["max_id"])

    @staticmethod
    def _load_index(
        organization_id: int,
    ) -> tuple[BM25Okapi | None, list[dict[str, Any]]]:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT dc.id AS chunk_id, dc.text, dc.chunk_index, dc.document_id,
                       d.filename, d.domain, d.source_type
                FROM doc_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.organization_id = ? AND d.status = 'active'
                """,
                (organization_id,),
            ).fetchall()
        if not rows:
            return None, []
        chunks = [dict(row) for row in rows]
        return BM25Okapi([tokenize(c["text"]) for c in chunks]), chunks

    def _get_index(
        self, organization_id: int
    ) -> tuple[BM25Okapi | None, list[dict[str, Any]]]:
        with self._lock:
            fingerprint = self.content_fingerprint(organization_id)
            if (
                organization_id not in self._indexes
                or self._fingerprints.get(organization_id) != fingerprint
            ):
                self._indexes[organization_id] = self._load_index(organization_id)
                self._fingerprints[organization_id] = fingerprint
            return self._indexes[organization_id]

    def search(
        self,
        organization_id: int,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        allowed_document_ids: frozenset[int] | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        if allowed_document_ids is not None and not allowed_document_ids:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Scoring hors verrou : l'index (bm25, chunks) est immuable une fois construit.
        bm25, chunks = self._get_index(organization_id)
        if bm25 is None:
            return []

        domain_value = domain_filter_value(domain)
        scores = bm25.get_scores(query_tokens)
        results: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            # Aucun terme commun avec la question : ne doit pas polluer la fusion
            # RRF. (On teste la présence des termes plutôt que score > 0 : sur un
            # très petit corpus, l'IDF de BM25Okapi peut être négatif.)
            doc_terms = bm25.doc_freqs[i]
            if not any(t in doc_terms for t in query_tokens):
                continue
            if (
                allowed_document_ids is not None
                and chunk["document_id"] not in allowed_document_ids
            ):
                continue
            if domain_value and chunk["domain"] != domain_value:
                continue
            metadata = {
                "document_id": chunk["document_id"],
                "filename": chunk["filename"],
                "domain": chunk["domain"] or "general",
                "source_type": chunk["source_type"] or "",
                "chunk_index": chunk["chunk_index"],
            }
            if filters and any(metadata.get(k) != v for k, v in filters.items()):
                continue
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "score": float(scores[i]),
                    "metadata": metadata,
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def mark_for_rebuild(self, organization_id: int) -> None:
        with self._lock:
            self._indexes.pop(organization_id, None)
            self._fingerprints.pop(organization_id, None)


bm25_search = BM25Search()
