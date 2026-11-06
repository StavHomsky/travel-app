"""Rating rule, coordinates validation, search and sorting."""


def test_rating_on_visited_location(client):
    response = client.post(
        "/api/v1/locations",
        json={"name": "Rome", "country": "Italy", "type": "city", "visited": True, "rating": 5},
    )
    assert response.status_code == 201
    assert response.get_json()["rating"] == 5


def test_rating_on_wishlist_location_is_rejected(client):
    response = client.post(
        "/api/v1/locations",
        json={"name": "Rome", "country": "Italy", "type": "city", "visited": False, "rating": 4},
    )
    assert response.status_code == 422
    assert response.get_json()["details"]["rating"] == "Only visited locations can be rated."


def test_rating_out_of_range_or_wrong_type(client):
    for bad in (0, 6, 3.5, "5", True):
        response = client.post(
            "/api/v1/locations",
            json={"name": "Rome", "country": "Italy", "type": "city", "visited": True, "rating": bad},
        )
        assert response.status_code == 422, bad
        assert "rating" in response.get_json()["details"]


def test_moving_back_to_wishlist_clears_rating(client, make_location):
    created = make_location(visited=True, rating=4)
    url = f"/api/v1/locations/{created['id']}"
    body = client.patch(url, json={"visited": False}).get_json()
    assert body["visited"] is False
    assert body["rating"] is None


def test_patch_rating_on_wishlist_is_rejected(client, make_location):
    created = make_location(visited=False)
    response = client.patch(f"/api/v1/locations/{created['id']}", json={"rating": 3})
    assert response.status_code == 422


def test_manual_coordinates(client, make_location):
    created = make_location(latitude=48.8566, longitude=2.3522)
    assert created["latitude"] == 48.8566

    url = f"/api/v1/locations/{created['id']}"
    assert client.patch(url, json={"latitude": 91, "longitude": 0}).status_code == 422
    assert client.patch(url, json={"latitude": 10}).status_code == 422  # needs both


def test_renaming_clears_old_coordinates(client, make_location):
    created = make_location(latitude=48.8566, longitude=2.3522)
    body = client.patch(f"/api/v1/locations/{created['id']}", json={"name": "Lyon"}).get_json()
    assert body["latitude"] is None


def test_search_and_sort(client, make_location):
    make_location(name="Paris", visited=True, rating=3)
    make_location(name="Lyon", visited=True, rating=5)
    make_location(name="Tokyo", country="Japan")

    names = lambda url: [loc["name"] for loc in client.get(url).get_json()["items"]]  # noqa: E731

    assert names("/api/v1/locations?q=pAr") == ["Paris"]
    assert names("/api/v1/locations?q=france&sort=name") == ["Lyon", "Paris"]
    # unrated places always go last
    assert names("/api/v1/locations?sort=rating&order=desc") == ["Lyon", "Paris", "Tokyo"]
    assert names("/api/v1/locations?sort=rating&order=asc") == ["Paris", "Lyon", "Tokyo"]

    assert client.get("/api/v1/locations?sort=password").status_code == 400
    assert client.get("/api/v1/locations?order=up").status_code == 400


def test_stats_include_ratings(client, make_location):
    make_location(name="Paris", visited=True, rating=3)
    make_location(name="Lyon", visited=True, rating=5)
    body = client.get("/api/v1/stats").get_json()
    assert body["average_rating"] == 4.0
    assert body["by_rating"] == {"3": 1, "5": 1}


def test_import_applies_rating_rule(client):
    items = [{"name": "Rome", "country": "Italy", "type": "city", "visited": False, "rating": 5}]
    response = client.post("/api/v1/locations/import", json=items)
    assert response.status_code == 422
    assert response.get_json()["details"]["0"]["rating"] == "Only visited locations can be rated."
