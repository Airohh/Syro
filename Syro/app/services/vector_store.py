"""Stockage vectoriel Qdrant : une seule collection, filtrée par payload.

Chaque point porte `organization_id`, `document_id` et `domain` (indexés).
Le multi-tenant et le multi-domaine sont donc de simples filtres, ce qui
évite la prolifération de collections et les points orphelins lorsqu'un
document change de domaine.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    HnswConfigDiff,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from ..config import settings

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    pass


_UPSERT_BATCH_SIZE = 256
_INDEXED_FIELDS = {
    "organization_id": PayloadSchemaType.INTEGER,
    "document_id": PayloadSchemaType.INTEGER,
    "domain": PayloadSchemaType.KEYWORD,
}

# Client partagé (un seul pool HTTP) + collection vérifiée une fois par process.
_shared_client: QdrantClient | None = None
_collection_ready: set[str] = set()
_lock = threading.Lock()


def _get_shared_client() -> QdrantClient:
    global _shared_client
    if _shared_client is None:
        try:
            client = QdrantClient(
                url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=10
            )
            client.get_collections()  # valide la connexion une seule fois
            _shared_client = client
        except Exception as e:
            raise VectorStoreError(
                f"Failed to connect to Qdrant at {settings.qdrant_url}: {e}"
            ) from e
    return _shared_client


def _reset_shared_client() -> None:
    """Force une reconnexion au prochain appel (après une erreur réseau)."""
    global _shared_client
    _shared_client = None
    _collection_ready.clear()


def domain_filter_value(domain: str | None) -> str | None:
    """`None`/`general` = pas de filtre de domaine (recherche sur tout)."""
    if not domain or domain == "general":
        return None
    return domain


def build_filter(
    organization_id: int,
    domain: str | None = None,
    allowed_document_ids: frozenset[int] | None = None,
    filters: dict[str, Any] | None = None,
) -> Filter:
    must: list[FieldCondition] = [
        FieldCondition(key="organization_id", match=MatchValue(value=organization_id))
    ]
    domain_value = domain_filter_value(domain)
    if domain_value:
        must.append(FieldCondition(key="domain", match=MatchValue(value=domain_value)))
    if allowed_document_ids is not None:
        must.append(
            FieldCondition(
                key="document_id", match=MatchAny(any=sorted(allowed_document_ids))
            )
        )
    for key, value in (filters or {}).items():
        must.append(FieldCondition(key=key, match=MatchValue(value=value)))
    return Filter(must=must)


class VectorStore:
    def __init__(self, collection_name: str | None = None) -> None:
        self.collection_name = collection_name or settings.qdrant_collection_name

    def _client(self) -> QdrantClient:
        return _get_shared_client()

    def ensure_collection(self) -> None:
        if self.collection_name in _collection_ready:
            return
        with _lock:
            if self.collection_name in _collection_ready:
                return
            client = self._client()
            existing = {c.name for c in client.get_collections().collections}
            if self.collection_name not in existing:
                client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimensions,
                        distance=Distance.COSINE,
                    ),
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=128),
                )
            else:
                info = client.get_collection(self.collection_name)
                size = getattr(info.config.params.vectors, "size", None)
                if size is not None and size != settings.embedding_dimensions:
                    raise VectorStoreError(
                        f"Collection '{self.collection_name}' has vectors of size "
                        f"{size} but EMBEDDING_DIMENSIONS={settings.embedding_dimensions}. "
                        "Changing the embedding model requires a new collection "
                        "(set QDRANT_COLLECTION_NAME) and a reindex (make reindex)."
                    )
            for field, schema in _INDEXED_FIELDS.items():
                # Idempotent côté Qdrant ; indispensable pour filtrer vite.
                client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema,
                )
            _collection_ready.add(self.collection_name)

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[np.ndarray],
    ) -> None:
        """`chunks` = [{id: int, text: str, payload: dict}] (id = id SQLite)."""
        if not chunks:
            return
        try:
            self.ensure_collection()
            points = [
                PointStruct(
                    id=int(chunk["id"]),
                    vector=np.asarray(vec, dtype=np.float32).tolist(),
                    payload={"text": chunk["text"], **chunk["payload"]},
                )
                for chunk, vec in zip(chunks, embeddings)
            ]
            client = self._client()
            for start in range(0, len(points), _UPSERT_BATCH_SIZE):
                client.upsert(
                    collection_name=self.collection_name,
                    points=points[start : start + _UPSERT_BATCH_SIZE],
                )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            raise VectorStoreError(f"Failed to upsert chunks in Qdrant: {e}") from e

    def delete_document(self, document_id: int) -> None:
        try:
            self.ensure_collection()
            self._client().delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            raise VectorStoreError(f"Failed to delete chunks from Qdrant: {e}") from e

    def search(
        self,
        query_vector: np.ndarray,
        organization_id: int,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        domain: str | None = None,
        allowed_document_ids: frozenset[int] | None = None,
    ) -> list[dict[str, Any]]:
        if allowed_document_ids is not None and not allowed_document_ids:
            return []
        try:
            self.ensure_collection()
            response = self._client().query_points(
                collection_name=self.collection_name,
                query=np.asarray(query_vector, dtype=np.float32).tolist(),
                query_filter=build_filter(
                    organization_id, domain, allowed_document_ids, filters
                ),
                limit=top_k,
                with_payload=True,
            )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            raise VectorStoreError(f"Failed to search in Qdrant: {e}") from e

        return [
            {
                "chunk_id": point.id,
                "text": (point.payload or {}).get("text", ""),
                "score": point.score,
                "metadata": {
                    k: v for k, v in (point.payload or {}).items() if k != "text"
                },
            }
            for point in response.points
        ]

    def get_collection_status(self) -> dict[str, Any]:
        try:
            self.ensure_collection()
            info = self._client().get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vector_size": info.config.params.vectors.size,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            raise VectorStoreError(f"Failed to get collection status: {e}") from e
