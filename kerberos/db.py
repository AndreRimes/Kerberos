import os
import sqlite3
import threading
from contextlib import closing

from kerberos import config
from kerberos.crypto_utils import derive_key

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    salt BLOB NOT NULL,
    key BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS services (
    name TEXT PRIMARY KEY,
    key BLOB NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _lock, closing(_connect()) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def create_user(username: str, password: str) -> None:
    salt = os.urandom(16)
    key = derive_key(password, salt)
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, salt, key) VALUES (?, ?, ?)",
            (username, salt, key),
        )
        conn.commit()


def create_service(name: str, key: bytes = None) -> None:
    key = key or os.urandom(32)
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO services (name, key) VALUES (?, ?)",
            (name, key),
        )
        conn.commit()


def get_user_salt(username: str) -> bytes:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT salt FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        raise KeyError(f"Unknown user: {username}")
    return row[0]


def get_user_key(username: str) -> bytes:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT key FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        raise KeyError(f"Unknown user: {username}")
    return row[0]


def get_service_key(name: str) -> bytes:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT key FROM services WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise KeyError(f"Unknown service: {name}")
    return row[0]
