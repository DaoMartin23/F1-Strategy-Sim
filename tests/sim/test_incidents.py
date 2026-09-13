from sim.model import PARAMS, incident_chance, weather_at
from sim.race import new_race, step
from sim.rng import PURPOSE_DAMAGE_CHANCE, make_rng
from sim.types import Compound, Decision, EventType

_TRACK = "silverstone"
# Laps 1-9: safely before any rival's first planned pit (earliest two-stop
# target is ~lap 15), and the player never auto-pits, so every car is still
# on its starting MEDIUM compound and never pushing - conditions we can
# predict exactly without running a full simulation first.
_SEARCH_LAPS = range(1, 10)


def _find_incident(seed_range: range, car_id: int, want_dnf: bool) -> tuple[int, int] | None:
    dnf_probability = PARAMS["incident"]["dnf_given_incident_probability"]
    for seed in seed_range:
        for lap in _SEARCH_LAPS:
            wetness = weather_at(seed, _TRACK, lap)
            chance = incident_chance(Compound.MEDIUM, wetness, pushing=False)
            rng = make_rng(seed, lap, PURPOSE_DAMAGE_CHANCE, car_id)
            if rng.random() < chance:
                is_dnf = rng.random() < dnf_probability
                if is_dnf == want_dnf:
                    return seed, lap
    return None


def _drive_to(seed: int, target_lap: int) -> tuple[object, list[object]]:
    state = new_race(_TRACK, seed=seed, player_car="car_5", starting_position=10)
    while state.lap < target_lap - 1:
        state, _trace, _events = step(state, None, seed=state.seed)
    state, _trace, events = step(state, None, seed=state.seed)
    return state, events


def test_player_dnf_sets_retired_lap_and_raises_no_event() -> None:
    found = _find_incident(range(5000), car_id=0, want_dnf=True)
    assert found is not None, "expected to find a player DNF within the search range"
    seed, target_lap = found

    state, events = _drive_to(seed, target_lap)
    assert state.cars[0].retired_lap == target_lap
    assert not any(e.type is EventType.DAMAGE for e in events)


def test_player_damage_incident_raises_damage_event() -> None:
    found = _find_incident(range(5000), car_id=0, want_dnf=False)
    assert found is not None, "expected to find a player damage (non-DNF) incident"
    seed, target_lap = found

    state, events = _drive_to(seed, target_lap)
    assert state.cars[0].retired_lap is None
    assert state.cars[0].damage >= 1
    damage_events = [e for e in events if e.type is EventType.DAMAGE]
    assert len(damage_events) == 1
    assert set(damage_events[0].options) == {"repair", "stay_out"}


def test_rival_dnf_sets_retired_lap_and_raises_no_event() -> None:
    found = _find_incident(range(5000), car_id=3, want_dnf=True)
    assert found is not None, "expected to find a rival DNF within the search range"
    seed, target_lap = found

    state, events = _drive_to(seed, target_lap)
    rival = next(c for c in state.cars if c.id == 3)
    assert rival.retired_lap == target_lap
    assert all(e.type is not EventType.DAMAGE for e in events)


def test_rival_damage_never_raises_an_event() -> None:
    found = _find_incident(range(5000), car_id=3, want_dnf=False)
    assert found is not None, "expected to find a rival damage (non-DNF) incident"
    seed, target_lap = found

    state, events = _drive_to(seed, target_lap)
    rival = next(c for c in state.cars if c.id == 3)
    assert rival.retired_lap is None
    assert rival.damage >= 1
    assert all(e.type is not EventType.DAMAGE for e in events)


def test_repair_choice_resets_damage_and_pits() -> None:
    found = _find_incident(range(5000), car_id=0, want_dnf=False)
    assert found is not None
    seed, target_lap = found

    state, _events = _drive_to(seed, target_lap)
    assert state.cars[0].damage >= 1
    damaged_pit_count = state.cars[0].pit_count

    state, _trace, _events = step(state, Decision(choice="repair"), seed=state.seed)
    assert state.cars[0].damage == 0
    assert state.cars[0].tyre_age == 1
    assert state.cars[0].pit_count == damaged_pit_count + 1
