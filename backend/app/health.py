"""Kubernetes probes.

/healthz  - liveness: the process is up and serving requests (no dependencies).
/readyz   - readiness: the database is reachable, so traffic can be routed here.
"""
import logging

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from .extensions import db

health_bp = Blueprint("health", __name__)
log = logging.getLogger(__name__)


@health_bp.get("/healthz")
def liveness():
    return jsonify(status="ok", version=current_app.config["APP_VERSION"])


@health_bp.get("/readyz")
def readiness():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        log.warning("readiness check failed", exc_info=True)
        return jsonify(status="unavailable", database="down"), 503
    return jsonify(status="ready", database="up")
