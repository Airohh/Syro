"""Parcours complet via l'API : login → upload → ingestion → chat avec sources.

Qdrant tourne en mode local (mémoire), les embeddings sont factices mais
déterministes (sac de mots haché) et le LLM est simulé : on vérifie le
câblage réel de bout en bout, sans service externe.
"""

import hashlib
import re
from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.main import app
from app.services import vector_store

DIM = 64


def _bow_embed(texts):
    """Sac de mots haché → vecteur normalisé (similarité ≈ recouvrement lexical)."""
    out = []
    for text in texts:
        vec = np.zeros(DIM, dtype=np.float32)
        for word in re.findall(r"\w+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIM] += 1
        out.append(vec / (np.linalg.norm(vec) or 1))
    return out


@pytest.fixture
def api(syro_db, monkeypatch):
    client = QdrantClient(":memory:")
    monkeypatch.setattr(vector_store, "_get_shared_client", lambda: client)
    monkeypatch.setattr(vector_store.settings, "embedding_dimensions", DIM)
    monkeypatch.setattr(vector_store.settings, "celery_task_always_eager", True)
    monkeypatch.setattr(vector_store.settings, "enable_reranking", False)
    vector_store._collection_ready.clear()
    with patch("app.services.llm.provider._embed_texts", side_effect=_bow_embed):
        with TestClient(app) as c:
            token = c.post(
                "/auth/login",
                data={"username": "demo@syro.local", "password": "syro-demo"},
            ).json()["access_token"]
            c.headers["Authorization"] = f"Bearer {token}"
            yield c
    vector_store._collection_ready.clear()


def test_upload_then_chat_cites_the_document(api):
    doc = (
        "# Qdrant\n\nQdrant est une base de données vectorielle écrite en Rust. "
        "Elle supporte le filtrage par payload et l'index HNSW."
    )
    resp = api.post(
        "/documents/files",
        files={"file": ("qdrant.md", doc.encode(), "text/markdown")},
        data={"domain": "tech"},
    )
    assert resp.status_code == 200, resp.text
    doc_id = resp.json()["document_id"]

    status = api.get(f"/documents/{doc_id}").json()
    assert status["status"] == "complete", status
    assert status["domain"] == "tech"

    with patch(
        "app.services.chat.answer_from_context",
        return_value=("Qdrant est écrit en Rust [Source 1].", 12),
    ) as llm:
        chat = api.post("/chat/message", json={"content": "En quel langage est écrit Qdrant ?"})
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["sources"][0]["metadata"]["filename"] == "qdrant.md"
    assert body["sources"][0]["metadata"]["source"] == 1
    assert "Rust" in llm.call_args.args[1][0]["text"]

    # Question suivante dans la même conversation : l'historique est transmis.
    with patch("app.services.chat.answer_from_context", return_value=("ok", 1)) as llm2:
        api.post(
            "/chat/message",
            json={"content": "Et le filtrage payload ?", "conversation_id": body["conversation_id"]},
        )
    assert len(llm2.call_args.kwargs["conversation_history"]) == 2


def test_unsupported_file_type_rejected(api):
    resp = api.post(
        "/documents/files", files={"file": ("virus.exe", b"MZ", "application/octet-stream")}
    )
    assert resp.status_code == 415


def test_readiness_reports_components(api):
    ready = api.get("/health/ready").json()
    assert ready["qdrant"]["ok"] is True
    assert "reranker" in ready and "llm" in ready
