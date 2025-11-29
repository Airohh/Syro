"""BM25 lexical search service."""

from __future__ import annotations

import re
from typing import Any, Sequence

from rank_bm25 import BM25Okapi

from ..db import db_session

class BM25Search:
    def __init__(self) -> None:
        self._indexes: dict[int, tuple[BM25Okapi, list[dict[str, Any]]]] = {}
        self._needs_rebuild: set[int] = set()

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
                    d.tags
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
    ) -> list[dict[str, Any]]:
        if organization_id not in self._indexes or organization_id in self._needs_rebuild:
            self._rebuild_index(organization_id)
        
        bm25, chunk_data = self._indexes[organization_id]
        
        if not chunk_data or bm25 is None:
            return []
        
        tokenized_query = self._tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        results = [
            {
                "chunk_id": chunk_data[i]["chunk_id"],
                "text": chunk_data[i]["text"],
                "score": float(scores[i]),
                "metadata": {
                    "document_id": chunk_data[i]["document_id"],
                    "source_type": chunk_data[i]["source_type"] or "",
                    "tags": chunk_data[i]["tags"] or "",
                },
            }
            for i in range(len(chunk_data))
        ]
        
        if filters:
            filtered_results = []
            for result in results:
                match = True
                for key, value in filters.items():
                    if result["metadata"].get(key) != value:
                        match = False
                        break
                if match:
                    filtered_results.append(result)
            results = filtered_results
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def mark_for_rebuild(self, organization_id: int) -> None:
        self._needs_rebuild.add(organization_id)
        if organization_id in self._indexes:
            del self._indexes[organization_id]

bm25_search = BM25Search()

