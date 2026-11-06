import io
import json


def test_create_location_returns_201_and_normalises(client):
    response = client.post(
        "/api/v1/locations",
        json={"name": "  Tokyo ", "country": "Japan", "type": "CITY", "visited": True},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["name"] == "Tokyo"
    assert body["type"] == "city"
    assert body["visited"] is True
    assert response.headers["Location"] == f"/api/v1/locations/{body['id']}"


def test_create_requires_fields(client):
    response = client.post("/api/v1/locations", json={"name": ""})
    assert response.status_code == 422
    body = response.get_json()
    assert body["error"] == "Unprocessable Entity"
    assert set(body["details"]) == {"name", "country", "type"}


def test_create_rejects_unknown_fields_and_bad_types(client):
    response = client.post(
        "/api/v1/locations",
        json={"name": "A", "country": "B", "type": "c", "visited": "yes", "evil": 1},
    )
    assert response.status_code == 422
    details = response.get_json()["details"]
    assert details["visited"] == "Must be true or false."
    assert details["evil"] == "Unknown field."


def test_create_rejects_too_long_values(client):
    response = client.post(
        "/api/v1/locations", json={"name": "x" * 121, "country": "B", "type": "c"}
    )
    assert response.status_code == 422
    assert "name" in response.get_json()["details"]


def test_create_rejects_invalid_json(client):
    response = client.post(
        "/api/v1/locations", data="not json", content_type="application/json"
    )
    assert response.status_code == 400


def test_duplicate_returns_409(client, make_location):
    make_location()
    response = client.post(
        "/api/v1/locations", json={"name": "Paris", "country": "France", "type": "city"}
    )
    assert response.status_code == 409


def test_get_and_404(client, make_location):
    created = make_location()
    assert client.get(f"/api/v1/locations/{created['id']}").get_json()["name"] == "Paris"
    missing = client.get("/api/v1/locations/999")
    assert missing.status_code == 404
    assert missing.get_json()["message"] == "Location 999 not found."


def test_list_filters_and_pagination(client, make_location):
    make_location(name="Paris")
    make_location(name="Lyon", visited=True)
    make_location(name="Val Thorens", type="ski", visited=True)
    make_location(name="Tokyo", country="Japan")

    body = client.get("/api/v1/locations?country=france&per_page=2").get_json()
    assert body["total"] == 3
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    body = client.get("/api/v1/locations?type=ski").get_json()
    assert [loc["name"] for loc in body["items"]] == ["Val Thorens"]

    body = client.get("/api/v1/locations?visited=true").get_json()
    assert body["total"] == 2


def test_list_rejects_bad_query_params(client):
    assert client.get("/api/v1/locations?per_page=1000").status_code == 400
    assert client.get("/api/v1/locations?page=abc").status_code == 400
    assert client.get("/api/v1/locations?visited=maybe").status_code == 400


def test_put_patch_delete(client, make_location):
    created = make_location()
    url = f"/api/v1/locations/{created['id']}"

    response = client.put(url, json={"name": "Nice", "country": "France", "type": "beach"})
    assert response.status_code == 200
    assert response.get_json()["type"] == "beach"

    # PUT requires the full object
    assert client.put(url, json={"name": "Only name"}).status_code == 422

    response = client.patch(url, json={"visited": True})
    assert response.status_code == 200
    assert response.get_json()["visited"] is True
    assert response.get_json()["name"] == "Nice"

    assert client.patch(url, json={}).status_code == 422

    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404


def test_stats(client, make_location):
    make_location(name="Paris", visited=True)
    make_location(name="Tokyo", country="Japan")
    body = client.get("/api/v1/stats").get_json()
    assert body["total"] == 2
    assert body["visited"] == 1
    assert body["wishlist"] == 1
    assert body["by_country"] == {"France": 1, "Japan": 1}


def test_import_append_skips_duplicates(client, make_location):
    make_location()
    items = [
        {"id": 7, "name": "Paris", "country": "France", "type": "city", "visited": True},
        {"name": "Rome", "country": "Italy", "type": "city"},
    ]
    response = client.post("/api/v1/locations/import?mode=append", json=items)
    assert response.status_code == 201
    assert response.get_json() == {"mode": "append", "created": 1, "skipped": 1}
    assert client.get("/api/v1/stats").get_json()["total"] == 2


def test_import_replace_with_file_upload(client, make_location):
    make_location()
    data = json.dumps([{"name": "Rome", "country": "Italy", "type": "city"}]).encode()
    response = client.post(
        "/api/v1/locations/import?mode=replace",
        data={"file": (io.BytesIO(data), "locations.json")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    names = [loc["name"] for loc in client.get("/api/v1/locations/export").get_json()]
    assert names == ["Rome"]


def test_import_is_atomic(client, make_location):
    make_location()
    items = [{"name": "Rome", "country": "Italy", "type": "city"}, {"name": "Broken"}]
    response = client.post("/api/v1/locations/import?mode=replace", json=items)
    assert response.status_code == 422
    assert "1" in response.get_json()["details"]
    # nothing changed
    names = [loc["name"] for loc in client.get("/api/v1/locations/export").get_json()]
    assert names == ["Paris"]


def test_import_rejects_bad_mode_and_shape(client):
    assert client.post("/api/v1/locations/import?mode=merge", json=[]).status_code == 422
    assert client.post("/api/v1/locations/import", json={"a": 1}).status_code == 422


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.is_json
