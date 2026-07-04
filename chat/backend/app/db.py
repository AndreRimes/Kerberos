import sqlite3
import threading
import time
from contextlib import closing

from .config import Config

_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    username TEXT NOT NULL REFERENCES users(username),
    valid_until REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_by TEXT NOT NULL REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS group_members (
    group_id INTEGER NOT NULL REFERENCES groups(id),
    username TEXT NOT NULL REFERENCES users(username),
    PRIMARY KEY (group_id, username)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL REFERENCES users(username),
    recipient TEXT REFERENCES users(username),
    group_id INTEGER REFERENCES groups(id),
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    CHECK ((recipient IS NULL) != (group_id IS NULL))
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(Config.CHAT_DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, closing(_connect()) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


# --- users ---

def ensure_user(username: str) -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username) VALUES (?)", (username,))
        conn.commit()


def user_exists(username: str) -> bool:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE username = ?", (username,)
        ).fetchone()
    return row is not None


def list_users() -> list[str]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT username FROM users ORDER BY username").fetchall()
    return [row["username"] for row in rows]


# --- sessions ---

def create_session(token: str, username: str, valid_until: float) -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO sessions (token, username, valid_until) VALUES (?, ?, ?)",
            (token, username, valid_until),
        )
        conn.commit()


def get_session(token: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT username, valid_until FROM sessions WHERE token = ?", (
                token,)
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()


# --- groups ---

def create_group(name: str, created_by: str) -> int | None:
    """Creates a group with `created_by` as its first member.

    Returns the new group id, or None if the name is already taken.
    """
    with _lock, closing(_connect()) as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO groups (name, created_by) VALUES (?, ?)",
                (name, created_by),
            )
        except sqlite3.IntegrityError:
            return None
        conn.execute(
            "INSERT INTO group_members (group_id, username) VALUES (?, ?)",
            (cursor.lastrowid, created_by),
        )
        conn.commit()
        return cursor.lastrowid


def get_group(group_id: int) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT id, name, created_by FROM groups WHERE id = ?", (group_id,)
        ).fetchone()
    return dict(row) if row else None


def is_member(group_id: int, username: str) -> bool:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM group_members WHERE group_id = ? AND username = ?",
            (group_id, username),
        ).fetchone()
    return row is not None


def add_member(group_id: int, username: str) -> None:
    with _lock, closing(_connect()) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO group_members (group_id, username) VALUES (?, ?)",
            (group_id, username),
        )
        conn.commit()


def list_user_groups(username: str) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.name, g.created_by
            FROM groups g
            JOIN group_members m ON m.group_id = g.id
            WHERE m.username = ?
            ORDER BY g.name
            """,
            (username,),
        ).fetchall()
    return [dict(row) for row in rows]


# --- messages ---

def send_direct_message(sender: str, recipient: str, content: str) -> dict:
    created_at = time.time()
    with _lock, closing(_connect()) as conn:
        cursor = conn.execute(
            "INSERT INTO messages (sender, recipient, content, created_at) VALUES (?, ?, ?, ?)",
            (sender, recipient, content, created_at),
        )
        conn.commit()
    return {
        "id": cursor.lastrowid,
        "sender": sender,
        "recipient": recipient,
        "content": content,
        "created_at": created_at,
    }


def send_group_message(sender: str, group_id: int, content: str) -> dict:
    created_at = time.time()
    with _lock, closing(_connect()) as conn:
        cursor = conn.execute(
            "INSERT INTO messages (sender, group_id, content, created_at) VALUES (?, ?, ?, ?)",
            (sender, group_id, content, created_at),
        )
        conn.commit()
    return {
        "id": cursor.lastrowid,
        "sender": sender,
        "content": content,
        "created_at": created_at,
    }


def get_direct_messages(user_a: str, user_b: str) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, sender, recipient, content, created_at
            FROM messages
            WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?)
            ORDER BY id
            """,
            (user_a, user_b, user_b, user_a),
        ).fetchall()
    return [dict(row) for row in rows]


def get_group_messages(group_id: int) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT id, sender, content, created_at
            FROM messages
            WHERE group_id = ?
            ORDER BY id
            """,
            (group_id,),
        ).fetchall()
    return [dict(row) for row in rows]
