"""Enrichment with the external HTTP calls replaced by fakes."""
import pytest
import requests

from app import enrichment


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


NOMINATIM_PARIS = [{"lat": "48.8588897", "lon": "2.3200410"}]
WIKI_PARIS = {
    "type": "standard",
    "extract": "Paris is the capital of France.",
    "thumbnail": {"source": "https://upload.wikimedia.org/paris.jpg"},
    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Paris"}},
}


@pytest.fixture()
def fake_http(app, monkeypatch):
    """Turn enrichment on and route requests.get to canned answers."""
    app.config["ENRICHMENT_ENABLED"] = True
    calls = []
    answers = {
        "nominatim": FakeResponse(payload=NOMINATIM_PARIS),
        "wikipedia": FakeResponse(payload=WIKI_PARIS),
    }

    def fake_get(url, params=None, timeout=None, headers=None):
        calls.append(url)
        assert timeout and "User-Agent" in headers
        answer = answers["nominatim" if "nominatim" in url else "wikipedia"]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(enrichment.requests, "get", fake_get)
    return answers, calls


def test_create_enriches_location(client, fake_http):
    body = client.post(
        "/api/v1/locations", json={"name": "Paris", "country": "France", "type": "city"}
    ).get_json()
    assert body["latitude"] == pytest.approx(48.8588897)
    assert body["longitude"] == pytest.approx(2.3200410)
    assert body["description"] == "Paris is the capital of France."
    assert body["image_url"].endswith("paris.jpg")
    assert body["wiki_url"] == "https://en.wikipedia.org/wiki/Paris"


def test_manual_coordinates_skip_geocoding(client, fake_http):
    _, calls = fake_http
    body = client.post(
        "/api/v1/locations",
        json={"name": "Paris", "country": "France", "type": "city", "latitude": 1, "longitude": 2},
    ).get_json()
    assert body["latitude"] == 1
    assert not any("nominatim" in url for url in calls)


def test_api_failures_do_not_block_saving(client, fake_http):
    answers, _ = fake_http
    answers["nominatim"] = requests.ConnectionError("offline")
    answers["wikipedia"] = FakeResponse(status_code=500)
    response = client.post(
        "/api/v1/locations", json={"name": "Paris", "country": "France", "type": "city"}
    )
    assert response.status_code == 201
    assert response.get_json()["latitude"] is None
    assert response.get_json()["description"] is None

    metrics = client.get("/metrics").get_data(as_text=True)
    assert 'travel_enrichment_requests_total{result="error",source="geocoder"} 1.0' in metrics


def test_not_found_and_disambiguation(client, fake_http):
    answers, _ = fake_http
    answers["nominatim"] = FakeResponse(payload=[])
    answers["wikipedia"] = FakeResponse(payload={"type": "disambiguation", "extract": "Georgia may refer to"})
    body = client.post(
        "/api/v1/locations", json={"name": "Georgia", "country": "?", "type": "x"}
    ).get_json()
    assert body["latitude"] is None
    assert body["description"] is None


def test_refresh_endpoint(client, app, fake_http, make_location):
    app.config["ENRICHMENT_ENABLED"] = False
    created = make_location()
    assert created["latitude"] is None

    app.config["ENRICHMENT_ENABLED"] = True
    body = client.post(f"/api/v1/locations/{created['id']}/enrich").get_json()
    assert body["latitude"] == pytest.approx(48.8588897)
    assert client.post("/api/v1/locations/999/enrich").status_code == 404


def test_enrich_missing(app, fake_http, make_location):
    app.config["ENRICHMENT_ENABLED"] = False
    make_location(name="Paris")
    app.config["ENRICHMENT_ENABLED"] = True
    from app import services

    result = services.enrich_missing(delay=0)
    assert result == {"checked": 1, "updated": 1, "remaining": 0}


def test_enrich_missing_endpoint(client, app, fake_http, make_location, monkeypatch):
    app.config["ENRICHMENT_ENABLED"] = False
    make_location(name="Paris")
    make_location(name="Lyon")
    assert client.post("/api/v1/locations/enrich-missing").get_json()["checked"] == 0

    app.config["ENRICHMENT_ENABLED"] = True
    monkeypatch.setattr("app.services.time.sleep", lambda _s: None)
    body = client.post("/api/v1/locations/enrich-missing?limit=1").get_json()
    assert body == {"checked": 1, "updated": 1, "remaining": 1}
    assert client.post("/api/v1/locations/enrich-missing?limit=50").status_code == 400
