from flask import Blueprint, g, jsonify, request

from .. import db
from ..auth_middleware import login_required

groups_bp = Blueprint("groups", __name__)


def _membership_error(group_id: int):
    """Returns an error response if the caller can't act on the group, else None."""
    if db.get_group(group_id) is None:
        return jsonify(error="unknown group"), 404
    if not db.is_member(group_id, g.username):
        return jsonify(error="not a member of this group"), 403
    return None


@groups_bp.post("/api/groups")
@login_required
def create_group():
    name = (request.get_json(silent=True) or {}).get("name")
    if not name:
        return jsonify(error="name is required"), 400

    group_id = db.create_group(name, g.username)
    if group_id is None:
        return jsonify(error="group name already taken"), 409

    return jsonify(id=group_id, name=name, created_by=g.username), 201


@groups_bp.get("/api/groups")
@login_required
def my_groups():
    return jsonify(groups=db.list_user_groups(g.username))


@groups_bp.post("/api/groups/<int:group_id>/members")
@login_required
def add_member(group_id):
    error = _membership_error(group_id)
    if error:
        return error

    username = (request.get_json(silent=True) or {}).get("username")
    if not username:
        return jsonify(error="username is required"), 400

    if not db.user_exists(username):
        return jsonify(error="unknown user"), 404

    db.add_member(group_id, username)
    return jsonify(group_id=group_id, username=username), 201


@groups_bp.post("/api/groups/<int:group_id>/messages")
@login_required
def send_group_message(group_id):
    error = _membership_error(group_id)
    if error:
        return error

    content = (request.get_json(silent=True) or {}).get("content")
    if not content:
        return jsonify(error="content is required"), 400

    message = db.send_group_message(g.username, group_id, content)
    return jsonify(message), 201


@groups_bp.get("/api/groups/<int:group_id>/messages")
@login_required
def group_messages(group_id):
    error = _membership_error(group_id)
    if error:
        return error

    return jsonify(messages=db.get_group_messages(group_id))
