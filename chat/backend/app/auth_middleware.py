from functools import wraps

from flask import g, jsonify, request

from .sessions import get_session


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        scheme, _, token = auth_header.partition(" ")

        if scheme.lower() != "bearer" or not token:
            return jsonify(error="authentication required"), 401

        session = get_session(token)
        if session is None:
            return jsonify(error="invalid or expired token"), 401

        g.username = session["username"]
        g.token = token
        return view(*args, **kwargs)

    return wrapped
