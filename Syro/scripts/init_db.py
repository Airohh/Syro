import sqlite3
from pathlib import Path
import secrets

from passlib.context import CryptContext

import os

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("DB_PATH", str(ROOT / "db" / "syro.db")))
SCHEMA_PATH = ROOT / "db" / "schema.sql"

DEFAULT_ORG_NAME = "Syro Demo"
DEFAULT_OWNER_EMAIL = "owner@example.com"
DEFAULT_OWNER_PASSWORD = "ChangeMe123!"

# Initialize password context with error handling
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    # Fallback if bcrypt has issues
    import hashlib
    pwd_context = None

def hash_password(password: str) -> str:
    """Hash password using bcrypt. MUST use bcrypt for compatibility with backend."""
    if pwd_context is None:
        raise RuntimeError("bcrypt is required but not available. Install it with: pip install bcrypt")
    
    try:
        # Ensure password is not too long for bcrypt (72 bytes max)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    except Exception as e:
        raise RuntimeError(f"Failed to hash password with bcrypt: {e}. Install bcrypt: pip install bcrypt")

MIGRATION_PATH = ROOT / "db" / "migration_profiles_permissions.sql"


def _apply_migration(conn: sqlite3.Connection, migration_path: Path) -> None:
    """Apply migration SQL file.

    Uses executescript() so that BEGIN...END trigger bodies are handled
    correctly (simple semicolon-splitting breaks multi-statement triggers).
    For upgrades on existing DBs, ALTER TABLE errors for duplicate columns
    are caught and ignored.
    """
    sql = migration_path.read_text(encoding="utf-8")
    try:
        conn.executescript(sql)
        print("Migration applied.")
    except sqlite3.OperationalError as exc:
        msg = str(exc).lower()
        if "duplicate column" in msg or "already exists" in msg:
            # DB already partially migrated — fall back to statement-by-statement
            # for the non-trigger statements only, skipping duplicates.
            _apply_migration_incremental(conn, sql)
        else:
            raise


def _apply_migration_incremental(conn: sqlite3.Connection, sql: str) -> None:
    """Fallback: apply ALTER TABLE statements one by one, skipping duplicates.
    Used when executescript() fails because some columns already exist (upgrade path).
    """
    applied = skipped = 0
    # Extract only ALTER TABLE lines — safe to run one by one
    for line in sql.splitlines():
        stmt = line.strip().rstrip(";")
        if not stmt or stmt.startswith("--"):
            continue
        if stmt.upper().startswith("ALTER TABLE"):
            try:
                conn.execute(stmt)
                applied += 1
            except sqlite3.OperationalError as exc:
                if "duplicate column" in str(exc).lower():
                    skipped += 1
                else:
                    raise
    conn.commit()
    print(f"Migration (incremental): {applied} statements, {skipped} already present.")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        # Apply base schema (idempotent — uses CREATE TABLE IF NOT EXISTS)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # Apply migration for databases that existed before the schema was extended
        if MIGRATION_PATH.exists():
            _apply_migration(conn, MIGRATION_PATH)

        cur = conn.execute("SELECT COUNT(*) FROM organizations")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO organizations (name, credit_balance, max_members) VALUES (?, ?, ?)",
                (DEFAULT_ORG_NAME, 100000, 10),
            )
            org_id = conn.execute("SELECT id FROM organizations WHERE name = ?", (DEFAULT_ORG_NAME,)).fetchone()[0]
            conn.execute(
                "INSERT INTO users (organization_id, email, password_hash, role) VALUES (?, ?, ?, 'owner')",
                (org_id, DEFAULT_OWNER_EMAIL, hash_password(DEFAULT_OWNER_PASSWORD)),
            )
            conn.execute(
                "INSERT INTO api_keys (organization_id, name, secret) VALUES (?, ?, ?)",
                (org_id, "default", secrets.token_hex(32)),
            )
            conn.commit()
            print("Seeded default organization and owner user.")

    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
