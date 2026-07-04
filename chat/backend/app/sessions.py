import secrets
import time

from . import db


def create_session(username: str, valid_until: float) -> str:
    token = secrets.token_urlsafe(32)
    db.create_session(token, username, valid_until)
    return token


def get_session(token: str) -> dict | None:
    session = db.get_session(token)
    if session is None:
        return None

    if session["valid_until"] <= time.time():
        db.delete_session(token)
        return None

    return session
