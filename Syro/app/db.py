import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import settings

def get_connection() -> sqlite3.Connection:
    # check_same_thread=False permet l'utilisation dans différents threads
    # (nécessaire pour FastAPI/Starlette qui est asynchrone)
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def get_db():
    with db_session() as conn:
        yield conn
