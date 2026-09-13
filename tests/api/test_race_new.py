from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

_VALID_BODY = {"track": "silverstone", "seed": 1, "car": "car_5", "starting_position": 10}


def test_create_race_returns_valid_state() -> None:
    response = client.post("/race/new", json=_VALID_BODY)
    assert response.status_code == 200
    body = response.json()
    assert body["track"] == "silverstone"
    assert body["seed"] == 1
    assert body["starting_position"] == 10
    assert body["lap"] == 0
    assert len(body["cars"]) == 20
    assert body["cars"][0]["id"] == 0
    assert body["cars"][0]["car"] == "car_5"
    assert body["pending_decision"] is None
    assert body["decision_log"] == []


def test_create_race_state_is_under_5kb_over_the_wire() -> None:
    response = client.post("/race/new", json=_VALID_BODY)
    assert len(response.content) < 5000


def test_create_race_is_deterministic_for_same_seed() -> None:
    response1 = client.post("/race/new", json=_VALID_BODY)
    response2 = client.post("/race/new", json=_VALID_BODY)
    assert response1.json() == response2.json()


def test_create_race_rejects_unknown_track() -> None:
    body = {**_VALID_BODY, "track": "monaco"}
    response = client.post("/race/new", json=body)
    assert response.status_code == 422


def test_create_race_rejects_unknown_car() -> None:
    body = {**_VALID_BODY, "car": "car_99"}
    response = client.post("/race/new", json=body)
    assert response.status_code == 422


def test_create_race_rejects_out_of_range_starting_position() -> None:
    body = {**_VALID_BODY, "starting_position": 21}
    response = client.post("/race/new", json=body)
    assert response.status_code == 422

    body_low = {**_VALID_BODY, "starting_position": 0}
    response_low = client.post("/race/new", json=body_low)
    assert response_low.status_code == 422
