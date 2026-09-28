"""Réindexe tous les documents actifs (chunking + embeddings + Qdrant).

À lancer après un changement de modèle d'embedding, de préfixes ou de
chunking :  make reindex   (ou  python scripts/reindex.py)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import db_session  # noqa: E402
from app.services.ingestion import ingest_document  # noqa: E402


def main() -> int:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id, filename FROM documents WHERE status = 'active' ORDER BY id"
        ).fetchall()
    failed = 0
    for row in rows:
        try:
            n = ingest_document(row["id"])
            print(f"  OK   {row['filename']} ({n} chunks)")
        except Exception as exc:
            failed += 1
            print(f"  FAIL {row['filename']}: {exc}")
    print(f"{len(rows) - failed}/{len(rows)} documents réindexés")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
