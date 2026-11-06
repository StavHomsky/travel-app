"""Travel Locations REST API - application factory."""
from flask import Flask
from werkzeug.exceptions import HTTPException

from .config import get_config
from .extensions import db, migrate


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    app.config["ERROR_404_HELP"] = False  # keep Flask-RESTful 404 messages clean

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be set (it comes from a Kubernetes Secret in production).")

    from .logging_config import init_logging
    from .metrics import init_metrics

    init_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    init_metrics(app)

    from . import models  # noqa: F401 - register models with SQLAlchemy/Alembic
    from .api import api_bp
    from .cli import register_cli
    from .health import health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(api_bp)
    register_cli(app)

    @app.errorhandler(HTTPException)
    def json_http_error(error):
        # Errors outside the API blueprint (unknown URL, wrong method) are JSON too.
        return {"error": error.name, "message": error.description, "details": {}}, error.code

    return app
