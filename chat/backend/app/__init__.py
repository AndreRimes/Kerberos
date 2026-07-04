from flask import Flask

from . import db
from .config import Config
from .routes.auth import auth_bp
from .routes.groups import groups_bp
from .routes.health import health_bp
from .routes.messages import messages_bp


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_db()

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(groups_bp)

    return app
