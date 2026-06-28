"""Ingest the evaluation corpus so the RAGAS benchmark is reproducible.

Walks evaluation/corpus/<domain>/*.md, indexes each file into the running
Syro pipeline (chunk -> embed -> Qdrant) under organization 1. Runs the
ingestion synchronously (no Celery needed).

Prerequisites:
    - Qdrant running (docker compose up -d qdrant)
    - Embeddings backend reachable (Ollama nomic-embed-text or OpenAI)
    - DB initialised (python scripts/init_db.py)

Usage:
    cd Syro/Syro
    python evaluation/ingest_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
SYRO_ROOT = EVAL_DIR.parent
sys.path.insert(0, str(SYRO_ROOT))

from app.db import db_session
from app.services.ingestion import checksum_bytes, create_document_entry, process_document

CORPUS_DIR = EVAL_DIR / "corpus"
ORGANIZATION_ID = 1


def main() -> None:
    files = sorted(CORPUS_DIR.rglob("*.md"))
    if not files:
        print(f"No corpus files found under {CORPUS_DIR}")
        sys.exit(1)

    print(f"Ingesting {len(files)} corpus files into organization {ORGANIZATION_ID}\n")

    ok, failed = 0, 0
    for md in files:
        domain = md.parent.name  # corpus/<domain>/file.md
        content = md.read_bytes()
        with db_session() as db:
            doc_id, _ = create_document_entry(
                db,
                organization_id=ORGANIZATION_ID,
                filename=md.name,
                storage_path=str(md),
                mime_type="text/markdown",
                checksum=checksum_bytes(content),
                tags=[f"domain:{domain}"],
                source_type="corpus",
            )

        process_document(doc_id, ORGANIZATION_ID, str(md), "text/markdown", domain=domain)

        with db_session() as db:
            row = db.execute(
                "SELECT ingestion_status, chunk_count, ingestion_error FROM documents WHERE id = ?",
                (doc_id,),
            ).fetchone()

        status = row["ingestion_status"]
        if status == "complete":
            ok += 1
            print(f"  OK   [{domain}] {md.name} -> {row['chunk_count']} chunks")
        else:
            failed += 1
            print(f"  FAIL [{domain}] {md.name} -> {row['ingestion_error']}")

    print(f"\nDone: {ok} ingested, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
