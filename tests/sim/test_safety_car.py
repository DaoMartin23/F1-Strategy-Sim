import numpy as np

from sim.model import PARAMS
from sim.race import detect_safety_car, is_finished, new_race, step
from sim.types import EventType


def _find_draw_in_range(low: float, high: float) -> int:
    for seed in range(10000):
        if low <= np.random.default_rng(seed).random() < high:
            return seed
    raise AssertionError(f"no seed found with a first draw in [{low}, {high})")


def test_detect_safety_car_fires_on_low_draw() -> None:
    seed = _find_draw_in_range(0.0, PARAMS["safety_car"]["base_chance_per_lap"])
    event = detect_safety_car(incident_occurred=False, rng=np.random.default_rng(seed), lap=10)
    assert event is not None
    assert event.type is EventType.SAFETY_CAR
    assert event.lap == 10
    assert set(event.options) == {"pit_soft", "pit_medium", "pit_hard", "hold_position"}


def test_detect_safety_car_does_not_fire_on_high_draw() -> None:
    base = PARAMS["safety_car"]["base_chance_per_lap"]
    boosted = base + PARAMS["safety_car"]["incident_bonus"]
    seed = _find_draw_in_range(boosted, 1.0)
    event = detect_safety_car(incident_occurred=True, rng=np.random.default_rng(seed), lap=10)
    assert event is None


def test_detect_safety_car_boost_makes_the_difference() -> None:
    # A draw that lands strictly between the base and incident-boosted
    # chance: should not fire without an incident, but should fire with one.
    base = PARAMS["safety_car"]["base_chance_per_lap"]
    boosted = base + PARAMS["safety_car"]["incident_bonus"]
    seed = _find_draw_in_range(base, boosted)

    no_incident_event = detect_safety_car(incident_occurred=False, rng=np.random.default_rng(seed), lap=5)
    with_incident_event = detect_safety_car(incident_occurred=True, rng=np.random.default_rng(seed), lap=5)
    assert no_incident_event is None
    assert with_incident_event is not None


def test_safety_car_more_frequent_with_incidents_statistically() -> None:
    n = 5000
    no_incident_count = sum(
        1 for seed in range(n) if detect_safety_car(False, np.random.default_rng(seed), lap=1) is not None
    )
    with_incident_count = sum(
        1 for seed in range(n) if detect_safety_car(True, np.random.default_rng(seed), lap=1) is not None
    )
    assert with_incident_count > no_incident_count


def test_step_can_emit_safety_car_event_over_many_races() -> None:
    track = "silverstone"
    found = False
    for seed in range(300):
        state = new_race(track, seed=seed, player_car="car_5", starting_position=10)
        while not is_finished(state):
            state, _trace, events = step(state, None, seed=state.seed)
            if any(e.type is EventType.SAFETY_CAR for e in events):
                found = True
                break
        if found:
            break
    assert found
