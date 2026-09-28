"""Initialise (ou met à niveau) la base SQLite. Idempotent.

Appelé automatiquement au démarrage de l'API. Utilisable seul :
    python scripts/init_db.py

Compte de démo créé au premier lancement (surchargeable par variables d'env) :
    SYRO_ADMIN_EMAIL    (défaut : demo@syro.local)
    SYRO_ADMIN_PASSWORD (défaut : syro-demo)
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import sys
from pathlib import Path

import bcrypt

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "db" / "schema.sql"

DEFAULT_ORG_NAME = "Syro Demo"
DEFAULT_ADMIN_EMAIL = "demo@syro.local"
DEFAULT_ADMIN_PASSWORD = "syro-demo"

# Colonnes ajoutées au fil des versions : ajoutées aux anciennes bases.
_UPGRADE_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "first_name": "TEXT",
        "last_name": "TEXT",
        "avatar_url": "TEXT",
        "bio": "TEXT",
        "phone": "TEXT",
        "preferences": "TEXT",
        "last_login": "TEXT",
        "updated_at": "TEXT",
    },
    "organizations": {
        "org_type": "TEXT DEFAULT 'individual'",
        "company_name": "TEXT",
        "address": "TEXT",
        "contact_email": "TEXT",
        "settings": "TEXT",
    },
    "conversations": {"user_id": "INTEGER"},
    "documents": {
        "access_level_id": "INTEGER DEFAULT 1",
        "quality_level_id": "INTEGER DEFAULT 1",
        "created_by_user_id": "INTEGER",
        "access_notes": "TEXT",
        "domain": "TEXT",
    },
}


def _db_path() -> Path:
    return Path(os.environ.get("DB_PATH", str(ROOT / "db" / "syro.db")))


def _upgrade_columns(conn: sqlite3.Connection) -> None:
    for table, columns in _UPGRADE_COLUMNS.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if not existing:
            continue  # table absente : créée par schema.sql
        for column, ddl in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _backfill_domains(conn: sqlite3.Connection) -> None:
    """Anciennes versions : domaine stocké en tag « domain:<x> »."""
    rows = conn.execute(
        "SELECT id, tags FROM documents WHERE domain IS NULL AND tags LIKE '%domain:%'"
    ).fetchall()
    for doc_id, tags in rows:
        try:
            for tag in json.loads(tags):
                if isinstance(tag, str) and tag.startswith("domain:"):
                    conn.execute(
                        "UPDATE documents SET domain = ? WHERE id = ?",
                        (tag.split(":", 1)[1], doc_id),
                    )
                    break
        except (TypeError, ValueError):
            continue


def init_db(verbose: bool = True) -> None:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _upgrade_columns(conn)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8-sig"))
        _backfill_domains(conn)

        if conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0] == 0:
            email = os.environ.get("SYRO_ADMIN_EMAIL", DEFAULT_ADMIN_EMAIL)
            password = os.environ.get("SYRO_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)
            cur = conn.execute(
                "INSERT INTO organizations (name, credit_balance, max_members) VALUES (?, ?, ?)",
                (DEFAULT_ORG_NAME, 1_000_000, 10),
            )
            org_id = cur.lastrowid
            password_hash = bcrypt.hashpw(
                password.encode("utf-8")[:72], bcrypt.gensalt()
            ).decode("utf-8")
            conn.execute(
                "INSERT INTO users (organization_id, email, password_hash, role) "
                "VALUES (?, ?, ?, 'owner')",
                (org_id, email, password_hash),
            )
            conn.execute(
                "INSERT INTO api_keys (organization_id, name, secret) VALUES (?, ?, ?)",
                (org_id, "default", secrets.token_hex(32)),
            )
            if verbose:
                print(f"Created demo organization and owner account: {email}")
                if "SYRO_ADMIN_PASSWORD" not in os.environ:
                    print(
                        "  Default password in use — set SYRO_ADMIN_PASSWORD "
                        "before exposing Syro beyond your machine.",
                        file=sys.stderr,
                    )
        conn.commit()
    if verbose:
        print(f"Database ready at {db_path}")


if __name__ == "__main__":
    init_db()
