from flask import Blueprint, g, jsonify, request

from .. import db
from ..auth_middleware import login_required

messages_bp = Blueprint("messages", __name__)


@messages_bp.get("/api/users")
@login_required
def list_users():
    return jsonify(users=db.list_users())


@messages_bp.post("/api/messages")
@login_required
def send_message():
    data = request.get_json(silent=True) or {}
    recipient = data.get("to")
    content = data.get("content")

    if not recipient or not content:
        return jsonify(error="to and content are required"), 400

    if not db.user_exists(recipient):
        return jsonify(error="unknown user"), 404

    message = db.send_direct_message(g.username, recipient, content)
    return jsonify(message), 201


@messages_bp.get("/api/messages/<username>")
@login_required
def conversation(username):
    if not db.user_exists(username):
        return jsonify(error="unknown user"), 404

    return jsonify(messages=db.get_direct_messages(g.username, username))
