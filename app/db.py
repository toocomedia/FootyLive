import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "keys.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Drop and recreate for schema update (since it's a fresh feature and ephemeral)
        cursor.execute("DROP TABLE IF EXISTS api_keys")
        cursor.execute("""
            CREATE TABLE api_keys (
                key TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def delete_expired_keys() -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE expires_at <= CURRENT_TIMESTAMP")
        conn.commit()

def get_active_key_for_ip(ip: str) -> str | None:
    delete_expired_keys()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key FROM api_keys WHERE ip_address = ? AND expires_at > CURRENT_TIMESTAMP ORDER BY expires_at DESC LIMIT 1",
            (ip,)
        )
        row = cursor.fetchone()
        return row["key"] if row else None

def key_exists(api_key: str) -> bool:
    delete_expired_keys()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM api_keys WHERE key = ? AND expires_at > CURRENT_TIMESTAMP", (api_key,))
        return cursor.fetchone() is not None

def insert_key(api_key: str, ip: str, expires_at: datetime) -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO api_keys (key, ip_address, expires_at) VALUES (?, ?, ?)",
            (api_key, ip, expires_at)
        )
        conn.commit()

# Initialize database tables if they don't exist
init_db()
