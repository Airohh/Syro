"""BM25 lexical search service."""

from __future__ import annotations

import json
import re
import threading
from typing import Any

from rank_bm25 import BM25Okapi

from ..db import db_session


def _domain_from_tags(tags: str | None) -> str:
    if not tags:
        return ""
    tags = tags.strip()
    if tags.startswith("["):
        try:
            parsed = json.loads(tags)
            if isinstance(parsed, list) and parsed:
                return str(parsed[0])
        except json.JSONDecodeError:
            pass
    return tags.split(",")[0].strip()


class BM25Search:
    def __init__(self) -> None:
        self._indexes: dict[int, tuple[BM25Okapi, list[dict[str, Any]]]] = {}
        self._needs_rebuild: set[int] = set()
        self._fingerprints: dict[int, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def _content_fingerprint(self, organization_id: int) -> tuple[int, int]:
        """Empreinte (count, max id) des chunks actifs de l'org.

        L'index BM25 vit en mémoire par processus : l'ingestion faite par le
        worker Celery n'invalide pas l'index du processus API. Cette empreinte,
        recalculée à chaque recherche (1 requête SQL indexée), détecte les
        changements faits par un autre processus.
        """
        with db_session() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS chunk_count, COALESCE(MAX(dc.id), 0) AS max_chunk_id
                FROM doc_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.organization_id = ? AND d.status = 'active'
                """,
                (organization_id,),
            ).fetchone()
        return (row["chunk_count"], row["max_chunk_id"])

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def _rebuild_index(self, organization_id: int) -> None:
        with db_session() as conn:
            rows = conn.execute(
                """
                SELECT 
                    dc.id as chunk_id,
                    dc.text,
                    dc.document_id,
                    d.source_type,
                    d.tags,
                    d.access_level_id,
                    d.quality_level_id
                FROM doc_chunks dc
                JOIN documents d ON d.id = dc.document_id
                WHERE d.organization_id = ? AND d.status = 'active'
                """,
                (organization_id,),
            ).fetchall()

        if not rows:
            self._indexes[organization_id] = (None, [])
            self._needs_rebuild.discard(organization_id)
            return

        texts = [row["text"] for row in rows]
        tokenized_texts = [self._tokenize(text) for text in texts]

        bm25 = BM25Okapi(tokenized_texts)

        chunk_data = [
            {
                "chunk_id": row["chunk_id"],
                "text": row["text"],
                "document_id": row["document_id"],
                "source_type": row["source_type"],
                "tags": row["tags"],
                "domain": _domain_from_tags(row["tags"]),
                "access_level_id": row["access_level_id"],
                "quality_level_id": row["quality_level_id"],
            }
            for row in rows
        ]

        self._indexes[organization_id] = (bm25, chunk_data)
        self._needs_rebuild.discard(organization_id)

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

        with self._lock:
            fingerprint = self._content_fingerprint(organization_id)
            if (
                organization_id not in self._indexes
                or organization_id in self._needs_rebuild
                or self._fingerprints.get(organization_id) != fingerprint
            ):
                self._rebuild_index(organization_id)
                self._fingerprints[organization_id] = fingerprint

            bm25, chunk_data = self._indexes[organization_id]

            if not chunk_data or bm25 is None:
                return []

            eligible: list[int] = []
            for i, chunk in enumerate(chunk_data):
                doc_id = chunk["document_id"]
                if (
                    allowed_document_ids is not None
                    and doc_id not in allowed_document_ids
                ):
                    continue
                if domain and chunk.get("domain") and chunk["domain"] != domain:
                    continue
                if filters:
                    meta = {
                        "document_id": doc_id,
                        "source_type": chunk.get("source_type") or "",
                        "tags": chunk.get("tags") or "",
                        "domain": chunk.get("domain") or "",
                    }
                    if any(meta.get(key) != value for key, value in filters.items()):
                        continue
                eligible.append(i)

            if not eligible:
                return []

            tokenized_query = self._tokenize(query)
            scores = bm25.get_scores(tokenized_query)
            results: list[dict[str, Any]] = []
            for i in eligible:
                results.append(
                    {
                        "chunk_id": chunk_data[i]["chunk_id"],
                        "text": chunk_data[i]["text"],
                        "score": float(scores[i]),
                        "metadata": {
                            "document_id": chunk_data[i]["document_id"],
                            "source_type": chunk_data[i]["source_type"] or "",
                            "tags": chunk_data[i]["tags"] or "",
                            "domain": chunk_data[i].get("domain") or "",
                        },
                    }
                )

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

    def mark_for_rebuild(self, organization_id: int) -> None:
        with self._lock:
            self._needs_rebuild.add(organization_id)
            self._fingerprints.pop(organization_id, None)
            if organization_id in self._indexes:
                del self._indexes[organization_id]


bm25_search = BM25Search()
