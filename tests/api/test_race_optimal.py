from fastapi.testclient import TestClient

from api.main import app
from sim.optimal import find_optimal

client = TestClient(app)


def test_optimal_endpoint_matches_direct_find_optimal_call() -> None:
    response = client.post(
        "/race/optimal", json={"track": "silverstone", "seed": 7, "car": "car_5", "starting_position": 10}
    )
    assert response.status_code == 200
    body = response.json()

    direct_result = find_optimal("silverstone", seed=7, player_car="car_5", starting_position=10)

    assert body["total_time"] == direct_result.total_time
    assert body["positions"] == direct_result.positions
    assert body["strategy"]["push_policy"] == direct_result.strategy.push_policy.value
    assert len(body["strategy"]["stops"]) == len(direct_result.strategy.stops)
    for body_stop, direct_stop in zip(body["strategy"]["stops"], direct_result.strategy.stops):
        assert body_stop["target_lap"] == direct_stop.target_lap
        assert body_stop["compound"] == direct_stop.compound.value

    # Structural sanity checks on the same response, no extra (slow) calls.
    assert body["total_time"] > 0.0
    assert len(body["positions"]) > 0
    assert all(1 <= p <= 20 for p in body["positions"])


def test_optimal_endpoint_rejects_unknown_track() -> None:
    response = client.post(
        "/race/optimal", json={"track": "monaco", "seed": 1, "car": "car_5", "starting_position": 10}
    )
    assert response.status_code == 422


def test_optimal_endpoint_rejects_unknown_car() -> None:
    response = client.post(
        "/race/optimal", json={"track": "silverstone", "seed": 1, "car": "car_99", "starting_position": 10}
    )
    assert response.status_code == 422


def test_optimal_endpoint_rejects_out_of_range_starting_position() -> None:
    response = client.post(
        "/race/optimal", json={"track": "silverstone", "seed": 1, "car": "car_5", "starting_position": 25}
    )
    assert response.status_code == 422
