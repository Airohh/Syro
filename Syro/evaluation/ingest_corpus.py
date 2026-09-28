"""Ingère le corpus d'évaluation (evaluation/corpus/<domaine>/*.md) dans l'org 1.

Passe par le vrai pipeline (chunking → embeddings → SQLite + Qdrant), de
façon synchrone (pas besoin de Celery). Idempotent : les documents du corpus
d'un run précédent sont supprimés avant réingestion.

Prérequis : Qdrant + embeddings joignables (Ollama ou OpenAI).

    cd Syro && python evaluation/ingest_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SYRO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(SYRO_ROOT))

from app.db import db_session  # noqa: E402
from app.services.ingestion import (  # noqa: E402
    checksum_bytes,
    create_document_entry,
    ingest_document,
)
from app.services.vector_store import VectorStore  # noqa: E402

CORPUS_DIR = EVAL_DIR / "corpus"
ORGANIZATION_ID = 1


def clear_previous_corpus() -> None:
    """Supprime les documents `corpus` d'un run précédent (SQLite + Qdrant).

    Sans ça, chaque run ajouterait des doublons et fausserait les métriques.
    """
    with db_session() as db:
        rows = db.execute(
            "SELECT id FROM documents WHERE organization_id = ? AND source_type = 'corpus'",
            (ORGANIZATION_ID,),
        ).fetchall()
    if not rows:
        return

    store = VectorStore()
    for row in rows:
        store.delete_document(row["id"])
    with db_session() as db:
        db.execute(
            "DELETE FROM documents WHERE organization_id = ? AND source_type = 'corpus'",
            (ORGANIZATION_ID,),
        )
    print(f"Cleared {len(rows)} corpus documents from a previous run\n")


def main() -> None:
    files = sorted(p for p in CORPUS_DIR.rglob("*.md") if p.parent != CORPUS_DIR)
    if not files:
        print(f"No corpus files found under {CORPUS_DIR}")
        sys.exit(1)

    clear_previous_corpus()
    print(f"Ingesting {len(files)} corpus files into organization {ORGANIZATION_ID}\n")

    failed = 0
    for md in files:
        domain = md.parent.name  # corpus/<domaine>/fichier.md
        content = md.read_bytes()
        with db_session() as db:
            doc_id, _ = create_document_entry(
                db,
                organization_id=ORGANIZATION_ID,
                filename=md.name,
                storage_path=str(md),
                mime_type="text/markdown",
                checksum=checksum_bytes(content),
                tags=None,
                source_type="corpus",
                domain=domain,
            )
        try:
            n = ingest_document(doc_id)
            print(f"  OK   [{domain}] {md.name} -> {n} chunks")
        except Exception as exc:
            failed += 1
            print(f"  FAIL [{domain}] {md.name} -> {exc}")

    print(f"\nDone: {len(files) - failed} ingested, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
