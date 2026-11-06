"""Prometheus metrics.

* HTTP metrics (request count, latency histogram per route) come from
  prometheus-flask-exporter.
* travel_location_events_total is a custom counter for business events.
* LocationCollector is a custom exporter that reads the database at scrape
  time and exposes inventory gauges (locations by type/status, DB health).
"""
import logging

from flask import current_app
from prometheus_client import REGISTRY, CollectorRegistry, Counter
from prometheus_client.core import GaugeMetricFamily
from prometheus_flask_exporter import PrometheusMetrics
from sqlalchemy import func

log = logging.getLogger(__name__)

EXCLUDED_PATHS = ["/metrics", "/healthz", "/readyz", "/static"]


class LocationCollector:
    """Custom collector: queries the database on every scrape."""

    def __init__(self, app):
        self.app = app

    def describe(self):
        # Returning nothing stops prometheus_client from calling collect()
        # at registration time (when the database may not be reachable yet).
        return []

    def collect(self):
        from .extensions import db
        from .models import Location

        db_up = GaugeMetricFamily("travel_db_up", "1 if the database answered the last scrape query")
        try:
            with self.app.app_context():
                rows = (
                    db.session.query(Location.type, Location.visited, func.count(Location.id))
                    .group_by(Location.type, Location.visited)
                    .all()
                )
                countries = db.session.query(func.count(func.distinct(Location.country))).scalar()
                unmapped = Location.query.filter(Location.latitude.is_(None)).count()
        except Exception:  # noqa: BLE001 - any DB failure means "down"
            log.warning("metrics collector could not query the database", exc_info=True)
            db_up.add_metric([], 0)
            yield db_up
            return

        db_up.add_metric([], 1)
        yield db_up

        by_type = GaugeMetricFamily(
            "travel_locations",
            "Number of saved locations by type and status",
            labels=["type", "status"],
        )
        for type_, visited, count in rows:
            by_type.add_metric([type_, "visited" if visited else "wishlist"], count)
        yield by_type

        yield GaugeMetricFamily(
            "travel_countries", "Number of distinct countries saved", value=countries or 0
        )
        yield GaugeMetricFamily(
            "travel_locations_unmapped", "Locations without map coordinates", value=unmapped
        )


def init_metrics(app):
    if not app.config.get("METRICS_ENABLED", True):
        return

    # Tests create many apps per process; give each its own registry so
    # metric names do not collide. Production uses the default registry,
    # which also exports process_* and python_* metrics.
    registry = CollectorRegistry() if app.testing else REGISTRY

    exporter = PrometheusMetrics(
        app,
        registry=registry,
        group_by="url_rule",
        excluded_paths=EXCLUDED_PATHS,
    )
    exporter.info("travel_app_info", "Application build information", version=app.config["APP_VERSION"])

    events = Counter(
        "travel_location_events",
        "Location create/update/delete/import events",
        ["event"],
        registry=registry,
    )
    enrichment = Counter(
        "travel_enrichment_requests",
        "Calls to external enrichment APIs, by source and result",
        ["source", "result"],
        registry=registry,
    )
    registry.register(LocationCollector(app))
    app.extensions["travel_metrics"] = {"events": events, "enrichment": enrichment}


def record_event(event, amount=1):
    metrics = current_app.extensions.get("travel_metrics")
    if metrics and amount:
        metrics["events"].labels(event=event).inc(amount)


def record_enrichment(source, result):
    metrics = current_app.extensions.get("travel_metrics")
    if metrics:
        metrics["enrichment"].labels(source=source, result=result).inc()
