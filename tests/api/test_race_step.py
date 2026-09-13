from typing import Any

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

_ALL_EVENT_TYPES = {"rain_start", "rain_end", "damage", "overtaken", "safety_car", "pitting_opportunity"}


def _new_race(seed: int, car: str = "car_4", starting_position: int = 12) -> dict[str, Any]:
    response = client.post(
        "/race/new", json={"track": "silverstone", "seed": seed, "car": car, "starting_position": starting_position}
    )
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


def test_step_endpoint_advances_state() -> None:
    state = _new_race(seed=1)
    response = client.post("/race/step", json={"state": state, "decision": None})
    assert response.status_code == 200
    body = response.json()
    assert body["state"]["lap"] > state["lap"]
    assert isinstance(body["laps"], list) and len(body["laps"]) >= 1


def test_step_endpoint_response_state_under_5kb() -> None:
    state = _new_race(seed=1)
    response = client.post("/race/step", json={"state": state, "decision": None})
    import json as _json

    assert len(_json.dumps(response.json()["state"]).encode("utf-8")) < 5000


def test_step_endpoint_resolves_decision_and_continues() -> None:
    state = _new_race(seed=42)
    response = client.post("/race/step", json={"state": state, "decision": None})
    body = response.json()
    event = body["event"]
    assert event is not None, "expected at least one event for this seed"

    decision = {"choice": event["options"][0]}
    resumed = client.post("/race/step", json={"state": body["state"], "decision": decision})
    assert resumed.status_code == 200
    resumed_body = resumed.json()
    assert resumed_body["state"]["lap"] > body["state"]["lap"]
    assert len(resumed_body["state"]["decision_log"]) == 1
    assert resumed_body["state"]["decision_log"][0]["choice"] == decision["choice"]


def test_full_race_drives_to_completion_via_repeated_step_calls_and_hits_all_event_types() -> None:
    seen_event_types: set[str] = set()
    total_laps = 52
    for seed in range(60):
        state = _new_race(seed=seed)
        decision: dict[str, Any] | None = None
        for _ in range(300):
            step_response = client.post("/race/step", json={"state": state, "decision": decision})
            assert step_response.status_code == 200
            payload = step_response.json()
            state = payload["state"]
            event = payload["event"]
            if event is not None:
                seen_event_types.add(event["type"])
                decision = {"choice": event["options"][0]}
            else:
                decision = None
            if state["lap"] >= total_laps and event is None:
                break
        else:
            raise AssertionError("race did not finish within the iteration cap")
        if seen_event_types == _ALL_EVENT_TYPES:
            break

    assert seen_event_types == _ALL_EVENT_TYPES
