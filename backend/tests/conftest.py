import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_location(client):
    def _make(**overrides):
        payload = {"name": "Paris", "country": "France", "type": "city", "visited": False}
        payload.update(overrides)
        response = client.post("/api/v1/locations", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make
