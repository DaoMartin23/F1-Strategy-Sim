import dataclasses

from sim.model import PARAMS, incident_chance, weather_at
from sim.race import (
    EVENT_PRIORITY,
    _pick_priority_event,
    is_finished,
    new_race,
    run_to_next_decision,
    step,
)
from sim.rng import PURPOSE_DAMAGE_CHANCE, make_rng
from sim.types import Compound, Decision, Event, EventType

_TRACK = "silverstone"
_SEARCH_LAPS = range(1, 10)


def _find_player_dnf_seed() -> int:
    dnf_probability = PARAMS["incident"]["dnf_given_incident_probability"]
    for seed in range(5000):
        for lap in _SEARCH_LAPS:
            wetness = weather_at(seed, _TRACK, lap)
            chance = incident_chance(Compound.MEDIUM, wetness, pushing=False)
            rng = make_rng(seed, lap, PURPOSE_DAMAGE_CHANCE, 0)
            if rng.random() < chance and rng.random() < dnf_probability:
                return seed
    raise AssertionError("expected to find a player DNF within the search range")


def _auto_decision(event: Event | None) -> Decision | None:
    if event is None:
        return None
    return Decision(choice=event.options[0])


# --- EVENT_PRIORITY / _pick_priority_event --------------------------------


def test_event_priority_covers_all_six_event_types() -> None:
    assert set(EVENT_PRIORITY) == set(EventType)
    assert len(EVENT_PRIORITY) == len(set(EVENT_PRIORITY))


def test_pick_priority_event_picks_the_higher_priority_one() -> None:
    low = Event(type=EventType.PIT_OPPORTUNITY, lap=5, options=["stay_out"], context={})
    high = Event(type=EventType.DAMAGE, lap=5, options=["repair"], context={})
    assert _pick_priority_event([low, high]) is high
    assert _pick_priority_event([high, low]) is high


def test_pick_priority_event_single_event_returned_unchanged() -> None:
    only = Event(type=EventType.OVERTAKEN, lap=5, options=["push"], context={})
    assert _pick_priority_event([only]) is only


# --- run_to_next_decision basics ------------------------------------------


def test_run_to_next_decision_stops_exactly_on_first_event() -> None:
    state = new_race(_TRACK, seed=42, player_car="car_4", starting_position=12)
    new_state, laps, event = run_to_next_decision(state, None, seed=state.seed)
    if event is not None:
        assert laps[-1].lap == new_state.lap
        assert new_state.pending_decision == event
    else:
        # No event before the race finished for this seed.
        assert is_finished(new_state)


def test_run_to_next_decision_resumes_after_a_decision_is_supplied() -> None:
    state = new_race(_TRACK, seed=42, player_car="car_4", starting_position=12)
    state, _laps, event = run_to_next_decision(state, None, seed=state.seed)
    assert event is not None, "expected at least one event for this seed before checking resumption"

    decision = _auto_decision(event)
    resumed_state, more_laps, _next_event = run_to_next_decision(state, decision, seed=state.seed)
    assert len(more_laps) >= 1
    assert resumed_state.lap > state.lap


def test_run_to_next_decision_no_op_on_already_finished_race() -> None:
    total_laps = 52
    state = new_race(_TRACK, seed=1, player_car="car_5", starting_position=10)
    state = dataclasses.replace(state, lap=total_laps)
    new_state, laps, event = run_to_next_decision(state, None, seed=state.seed)
    assert laps == []
    assert event is None
    assert new_state == state


# --- player DNF free-runs to the finish -----------------------------------


def test_player_dnf_free_runs_to_finish_in_one_call() -> None:
    seed = _find_player_dnf_seed()
    state = new_race(_TRACK, seed=seed, player_car="car_5", starting_position=10)
    total_laps = 52

    final_state, laps, event = run_to_next_decision(state, None, seed=state.seed)

    assert event is None
    assert final_state.lap == total_laps
    assert final_state.cars[0].retired_lap is not None
    assert len(laps) == total_laps
    # Rivals kept racing to the end for the final classification.
    for car in final_state.cars:
        if car.id != 0 and car.retired_lap is None:
            assert car.total_time > 0.0


# --- equivalence with manual lap-by-lap replay -----------------------------


def _drive_manually(state: object, seed: int) -> object:
    pending_decision = None
    while not is_finished(state):  # type: ignore[arg-type]
        decision = _auto_decision(pending_decision)
        state, _trace, events = step(state, decision, seed=seed)  # type: ignore[arg-type]
        pending_decision = None
        if state.cars[0].retired_lap is None and events:  # type: ignore[attr-defined]
            pending_decision = _pick_priority_event(events)
            state = dataclasses.replace(state, pending_decision=pending_decision)  # type: ignore[arg-type]
    return state


def test_run_to_next_decision_matches_manual_lap_by_lap_replay() -> None:
    seed = 42
    start_state = new_race(_TRACK, seed=seed, player_car="car_4", starting_position=12)

    # Path A: drive purely through run_to_next_decision(), which internally
    # jumps multiple laps per call whenever no event fires.
    state_a = start_state
    decision = None
    while not is_finished(state_a):
        state_a, _laps, event = run_to_next_decision(state_a, decision, seed=state_a.seed)
        decision = _auto_decision(event)
        if event is None:
            break

    # Path B: drive one raw step() at a time, applying the identical
    # auto-decision policy whenever a decision is due.
    state_b = _drive_manually(start_state, seed)

    assert state_a == state_b
