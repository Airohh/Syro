"""VectorStore contre un vrai moteur Qdrant (mode local en mémoire)."""


import numpy as np
import pytest
from qdrant_client import QdrantClient

from app.services import vector_store
from app.services.vector_store import VectorStore, VectorStoreError


@pytest.fixture
def store(monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(vector_store, "_get_shared_client", lambda: client)
    monkeypatch.setattr(vector_store.settings, "embedding_dimensions", 3)
    vector_store._collection_ready.clear()
    yield VectorStore("test_chunks")
    vector_store._collection_ready.clear()


def _point(pid, org, doc, domain, vec):
    return (
        {"id": pid, "text": f"chunk {pid}", "payload": {
            "organization_id": org, "document_id": doc, "domain": domain,
            "filename": f"d{doc}.md",
        }},
        np.array(vec, dtype=np.float32),
    )


def _upsert(store, *points):
    store.upsert_chunks([p for p, _ in points], [v for _, v in points])


def test_search_is_scoped_by_org_domain_and_permissions(store):
    _upsert(
        store,
        _point(1, 1, 10, "tech", [1, 0, 0]),
        _point(2, 1, 11, "mlops", [0.9, 0.1, 0]),
        _point(3, 2, 12, "tech", [1, 0, 0]),  # autre organisation
    )
    q = np.array([1, 0, 0], dtype=np.float32)

    ids = lambda **kw: [r["chunk_id"] for r in store.search(q, 1, top_k=10, **kw)]  # noqa: E731
    assert ids() == [1, 2]
    assert ids(domain="tech") == [1]
    assert ids(domain="general") == [1, 2]
    assert ids(allowed_document_ids=frozenset({11})) == [2]

    hit = store.search(q, 1, top_k=1)[0]
    assert hit["metadata"]["filename"] == "d10.md"
    assert "text" not in hit["metadata"]


def test_delete_document_removes_all_its_points(store):
    _upsert(store, _point(1, 1, 10, "tech", [1, 0, 0]), _point(2, 1, 10, "tech", [0, 1, 0]),
            _point(3, 1, 11, "tech", [0, 0, 1]))
    store.delete_document(10)
    q = np.array([1, 1, 1], dtype=np.float32)
    assert [r["chunk_id"] for r in store.search(q, 1, top_k=10)] == [3]


def test_dimension_mismatch_is_explicit(store, monkeypatch):
    _upsert(store, _point(1, 1, 10, "tech", [1, 0, 0]))
    vector_store._collection_ready.clear()
    monkeypatch.setattr(vector_store.settings, "embedding_dimensions", 1536)
    with pytest.raises(VectorStoreError, match="EMBEDDING_DIMENSIONS"):
        store.ensure_collection()
