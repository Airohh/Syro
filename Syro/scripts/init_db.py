import sqlite3
from pathlib import Path
import secrets

from passlib.context import CryptContext

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "syro.db"
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

def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn, open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        conn.executescript(schema_file.read())

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
            print("Seeded default organization and owner user.")

    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
