from flask import Blueprint, g, jsonify, request

from .. import db
from ..auth_middleware import login_required
from ..kerberos_login import LoginError, LoginUnavailable, login as kerberos_login
from ..sessions import create_session

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify(error="username and password are required"), 400

    try:
        result = kerberos_login(username, password)
    except LoginUnavailable as exc:
        return jsonify(error=str(exc)), 503
    except LoginError as exc:
        return jsonify(error=str(exc)), 401

    db.ensure_user(result["username"])
    token = create_session(result["username"], result["valid_until"])

    return jsonify(
        token=token,
        username=result["username"],
        expires_at=result["valid_until"],
    )


@auth_bp.get("/api/auth/me")
@login_required
def me():
    return jsonify(username=g.username)


@auth_bp.post("/api/auth/logout")
@login_required
def logout():
    db.delete_session(g.token)
    return jsonify(ok=True)
