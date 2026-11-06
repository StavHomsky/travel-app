from app import create_app
from app.extensions import db


def test_liveness(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_readiness_ok(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.get_json()["database"] == "up"


def test_readiness_fails_when_db_down(app, client, monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db.session, "execute", boom)
    assert client.get("/readyz").status_code == 503


def test_metrics_exposes_custom_metrics(client, make_location):
    make_location(name="Paris", visited=True)
    make_location(name="Tokyo", country="Japan")
    client.get("/api/v1/locations")

    text = client.get("/metrics").get_data(as_text=True)
    assert "travel_db_up 1.0" in text
    assert 'travel_locations{status="visited",type="city"} 1.0' in text
    assert "travel_countries 2.0" in text
    assert 'travel_location_events_total{event="created"} 2.0' in text
    assert "flask_http_request_duration_seconds" in text
    assert "travel_app_info" in text


def test_seed_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-db"])
    assert "Seeded 8 locations" in result.output
    result = runner.invoke(args=["seed-db"])
    assert "skipping seed" in result.output


def test_unknown_url_returns_json(client):
    response = client.get("/no-such-page")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"


def test_wrong_method_returns_json(client):
    response = client.delete("/api/v1/stats")
    assert response.status_code == 405


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import app.config as config

    monkeypatch.setattr(config.ProductionConfig, "SECRET_KEY", None)
    try:
        create_app("production")
    except RuntimeError as exc:
        assert "SECRET_KEY" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
