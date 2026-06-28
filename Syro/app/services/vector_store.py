"""Qdrant vector store service for embeddings storage and retrieval."""

from __future__ import annotations

from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)

from ..config import settings
from .llm import get_embedding_vector, get_embedding_vectors

class VectorStoreError(Exception):
    pass


# Client Qdrant partagé au niveau module : un seul QdrantClient (donc un seul
# pool de connexions HTTP) réutilisé par toutes les instances VectorStore et
# toutes les requêtes. Avant, chaque `VectorStore()` recréait un client et
# refaisait un `get_collections()` de health-check à CHAQUE opération.
_shared_client: QdrantClient | None = None

# Nombre de points par upsert. Évite un seul upsert géant pour un gros document
# (et reste bien plus efficace qu'un upsert par chunk).
_UPSERT_BATCH_SIZE = 256


def _get_shared_client() -> QdrantClient:
    global _shared_client
    if _shared_client is None:
        try:
            client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=10,
            )
            client.get_collections()  # valide la connexion une seule fois
            _shared_client = client
        except Exception as e:
            error_msg = f"Failed to connect to Qdrant at {settings.qdrant_url}: {str(e)}"
            raise VectorStoreError(error_msg) from e
    return _shared_client


def _reset_shared_client() -> None:
    """Force une reconnexion au prochain appel (après une erreur réseau)."""
    global _shared_client
    _shared_client = None

class VectorStore:
    def __init__(self, collection_name: str | None = None, domain: str | None = None) -> None:
        if collection_name:
            self.collection_name = collection_name
        elif domain:
            self.collection_name = self._get_collection_for_domain(domain)
        else:
            self.collection_name = settings.qdrant_collection_name
    @staticmethod
    def _get_collection_for_domain(domain: str) -> str:
        if not getattr(settings, 'enable_domain_routing', True):
            return settings.qdrant_collection_name
        
        if not domain or domain == "general":
            return settings.qdrant_collection_name
        
        base_name = settings.qdrant_collection_name.replace("_chunks", "")
        return f"{base_name}_{domain}_chunks"

    def _get_client(self) -> QdrantClient:
        return _get_shared_client()

    def _ensure_collection(self, collection_name: str | None = None) -> None:
        try:
            client = self._get_client()
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            target_collection = collection_name or self.collection_name
            
            if target_collection not in collection_names:
                from qdrant_client.models import HnswConfigDiff, OptimizersConfigDiff
                
                if settings.performance_mode == "fast":
                    hnsw_config = HnswConfigDiff(m=16, ef_construct=64)
                    optimizer_config = OptimizersConfigDiff(indexing_threshold=10000)
                else:
                    hnsw_config = HnswConfigDiff(m=32, ef_construct=200)
                    optimizer_config = OptimizersConfigDiff(indexing_threshold=20000)
                
                client.create_collection(
                    collection_name=target_collection,
                    vectors_config={
                        "size": settings.embedding_dimensions,
                        "distance": Distance.COSINE,
                        "hnsw_config": hnsw_config,
                    },
                    optimizers_config=optimizer_config,
                )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to ensure collection '{self.collection_name}': {str(e)}"
            raise VectorStoreError(error_msg) from e

    def add_chunk(
        self,
        chunk_id: str,
        organization_id: int,
        document_id: int,
        text: str,
        embedding: np.ndarray | None = None,
        metadata: dict[str, Any] | None = None,
        domain: str | None = None,
    ) -> None:
        try:
            target_collection = self._get_collection_for_domain(domain) if domain else self.collection_name
            self._ensure_collection(target_collection)
            
            client = self._get_client()
            
            if embedding is None:
                embedding = get_embedding_vector(text)
            
            try:
                point_id = int(chunk_id.split("_")[-1]) if "_" in chunk_id else int(chunk_id)
            except (ValueError, IndexError):
                point_id = abs(hash(chunk_id)) % (2**63)
            
            payload = {
                "chunk_id": chunk_id,
                "organization_id": organization_id,
                "document_id": document_id,
                "text": text,
                **(metadata or {}),
            }
            
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload=payload,
            )
            
            client.upsert(
                collection_name=target_collection,
                points=[point],
            )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to add chunk to Qdrant: {str(e)}"
            raise VectorStoreError(error_msg) from e

    def add_chunks_batch(
        self,
        chunks: list[dict[str, Any]],
        organization_id: int,
        document_id: int,
        domain: str | None = None,
    ) -> None:
        """Indexe plusieurs chunks en lot. `chunks` = liste de dicts
        {chunk_id: str, text: str, metadata: dict}. Embeddings calculés en un
        seul appel réseau, collection vérifiée une fois, upsert par paquets.
        Remplace N×(ensure_collection + embed + upsert) par 1+1+ceil(N/256)."""
        if not chunks:
            return
        try:
            target_collection = self._get_collection_for_domain(domain) if domain else self.collection_name
            self._ensure_collection(target_collection)
            client = self._get_client()

            texts = [c["text"] for c in chunks]
            embeddings = get_embedding_vectors(texts)

            points: list[PointStruct] = []
            for chunk, embedding in zip(chunks, embeddings):
                chunk_id = chunk["chunk_id"]
                try:
                    point_id = int(chunk_id.split("_")[-1]) if "_" in chunk_id else int(chunk_id)
                except (ValueError, IndexError):
                    point_id = abs(hash(chunk_id)) % (2**63)

                payload = {
                    "chunk_id": chunk_id,
                    "organization_id": organization_id,
                    "document_id": document_id,
                    "text": chunk["text"],
                    **(chunk.get("metadata") or {}),
                }
                points.append(PointStruct(id=point_id, vector=embedding.tolist(), payload=payload))

            for start in range(0, len(points), _UPSERT_BATCH_SIZE):
                client.upsert(
                    collection_name=target_collection,
                    points=points[start:start + _UPSERT_BATCH_SIZE],
                )
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to add chunks batch to Qdrant: {str(e)}"
            raise VectorStoreError(error_msg) from e

    def delete_chunks_by_document(self, document_id: int, domain: str | None = None) -> None:
        try:
            client = self._get_client()
            target_collection = self._get_collection_for_domain(domain) if domain else self.collection_name
            
            doc_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

            # Paginate: un document peut avoir plus de chunks que la limite
            # d'un seul scroll (sinon les points au-delà restent orphelins).
            while True:
                points, next_page_offset = client.scroll(
                    collection_name=target_collection,
                    scroll_filter=doc_filter,
                    limit=100,
                )
                if points:
                    client.delete(
                        collection_name=target_collection,
                        points_selector=[point.id for point in points],
                    )
                if not points or next_page_offset is None:
                    break
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to delete chunks from Qdrant: {str(e)}"
            raise VectorStoreError(error_msg) from e

    def search(
        self,
        query_vector: np.ndarray,
        organization_id: int,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        domain: str | None = None,
        allowed_document_ids: frozenset[int] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            if allowed_document_ids is not None and not allowed_document_ids:
                return []

            client = self._get_client()
            target_collection = self._get_collection_for_domain(domain) if domain else self.collection_name
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="organization_id",
                        match=MatchValue(value=organization_id),
                    )
                ]
            )

            if allowed_document_ids is not None:
                query_filter.must.append(
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=sorted(allowed_document_ids)),
                    )
                )
            
            if filters:
                for key, value in filters.items():
                    query_filter.must.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
            
            results = client.search(
                collection_name=target_collection,
                query_vector=query_vector.tolist(),
                query_filter=query_filter,
                limit=top_k,
            )
            
            return [
                {
                    "chunk_id": result.id,
                    "text": result.payload.get("text", ""),
                    "score": result.score,
                    "metadata": {k: v for k, v in result.payload.items() if k not in ("text", "chunk_id")},
                }
                for result in results
            ]
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to search in Qdrant: {str(e)}"
            raise VectorStoreError(error_msg) from e

    def get_collection_status(self, domain: str | None = None) -> dict[str, Any]:
        try:
            client = self._get_client()
            target_collection = self._get_collection_for_domain(domain) if domain else self.collection_name
            info = client.get_collection(target_collection)
            return {
                "name": target_collection,
                "vector_size": info.config.params.vectors.size,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except VectorStoreError:
            raise
        except Exception as e:
            _reset_shared_client()
            error_msg = f"Failed to get collection status: {str(e)}"
            raise VectorStoreError(error_msg) from e

