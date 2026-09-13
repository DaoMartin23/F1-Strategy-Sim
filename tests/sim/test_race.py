import dataclasses

from sim.model import TRACKS
from sim.race import is_finished, step
from sim.types import CarState, Compound, Decision, State


def _car(
    car_id: int,
    car: str = "car_1",
    tyre_age: int = 5,
    total_time: float = 0.0,
    damage: int = 0,
    retired_lap: int | None = None,
) -> CarState:
    return CarState(
        id=car_id,
        car=car,
        compound=Compound.MEDIUM,
        tyre_age=tyre_age,
        pit_count=0,
        damage=damage,
        total_time=total_time,
        retired_lap=retired_lap,
    )


def _state(cars: list[CarState], lap: int = 0) -> State:
    return State(
        track="silverstone",
        seed=123,
        lap=lap,
        push_active=False,
        starting_position=1,
        player_strategy=[],
        pending_decision=None,
        decision_log=[],
        cars=cars,
    )


def test_step_advances_lap_by_one() -> None:
    state = _state([_car(0), _car(1)])
    new_state, trace, events = step(state, None, seed=state.seed)
    assert new_state.lap == 1
    assert trace.lap == 1
    assert events == []


def test_step_increases_total_time_for_every_car() -> None:
    state = _state([_car(0), _car(1), _car(2)])
    new_state, _trace, _events = step(state, None, seed=state.seed)
    for old_car, new_car in zip(state.cars, new_state.cars):
        assert new_car.total_time > old_car.total_time


def test_step_ages_tyres_by_one_lap_with_no_decision() -> None:
    state = _state([_car(0, tyre_age=5)])
    new_state, _trace, _events = step(state, None, seed=state.seed)
    assert new_state.cars[0].tyre_age == 6


def test_step_pit_resets_tyre_age_and_bumps_pit_count() -> None:
    state = _state([_car(0, tyre_age=20), _car(1, tyre_age=20)])
    decision = Decision(choice="pit_hard")
    new_state, _trace, _events = step(state, decision, seed=state.seed)
    assert new_state.cars[0].compound == Compound.HARD
    assert new_state.cars[0].tyre_age == 1
    assert new_state.cars[0].pit_count == 1
    # only the player (id 0) is affected by the decision
    assert new_state.cars[1].pit_count == 0


def test_step_pit_adds_time_versus_staying_out() -> None:
    state = _state([_car(0, tyre_age=20)])
    pit_state, _pit_trace, _e1 = step(state, Decision(choice="pit_hard"), seed=state.seed)
    stay_state, _stay_trace, _e2 = step(state, None, seed=state.seed)
    pit_delta = pit_state.cars[0].total_time - state.cars[0].total_time
    stay_delta = stay_state.cars[0].total_time - state.cars[0].total_time
    # Same seed/lap/car_id means identical noise draws, isolating the pit
    # loss + fresh-tyre effect: pit_loss alone is >=18s, dwarfing the small
    # tyre_deg difference between a fresh and a worn (but pre-cliff) tyre.
    assert pit_delta - stay_delta > 15.0


def test_step_clears_pending_decision_after_resolving() -> None:
    from sim.types import Event, EventType

    state = dataclasses.replace(
        _state([_car(0)]),
        pending_decision=Event(type=EventType.PIT_OPPORTUNITY, lap=1, options=["pit_hard", "stay_out"], context={}),
    )
    new_state, _trace, _events = step(state, Decision(choice="stay_out"), seed=state.seed)
    assert new_state.pending_decision is None


def test_step_push_reduces_lap_time_and_increases_wear() -> None:
    base = _state([_car(0, tyre_age=5)])
    pushed, push_trace, _e1 = step(base, Decision(push=True), seed=base.seed)
    normal, normal_trace, _e2 = step(base, Decision(push=False), seed=base.seed)
    assert push_trace.cars[0].lap_time < normal_trace.cars[0].lap_time
    assert pushed.cars[0].tyre_age > normal.cars[0].tyre_age
    assert pushed.push_active is True


def test_step_choice_push_activates_push_active() -> None:
    # Answering an OVERTAKEN event with choice="push" (its literal option
    # string) must actually engage push, not just set an unused string.
    state = _state([_car(0, tyre_age=5)])
    new_state, _trace, _events = step(state, Decision(choice="push"), seed=state.seed)
    assert new_state.push_active is True


def test_step_choice_hold_position_deactivates_push() -> None:
    state = dataclasses.replace(_state([_car(0, tyre_age=5)]), push_active=True)
    new_state, _trace, _events = step(state, Decision(choice="hold_position"), seed=state.seed)
    assert new_state.push_active is False


def test_step_choice_push_overrides_explicit_push_field() -> None:
    state = _state([_car(0, tyre_age=5)])
    new_state, _trace, _events = step(state, Decision(choice="push", push=False), seed=state.seed)
    assert new_state.push_active is True


def test_step_ranks_car_lap_positions_by_total_time() -> None:
    state = _state([_car(0, total_time=100.0), _car(1, total_time=50.0), _car(2, total_time=150.0)])
    _new_state, trace, _events = step(state, None, seed=state.seed)
    by_id = {c.id: c.position for c in trace.cars}
    assert by_id[1] == 1
    assert by_id[0] == 2
    assert by_id[2] == 3


def test_is_finished_true_only_at_last_lap() -> None:
    total_laps = TRACKS["silverstone"]["laps"]
    state = _state([_car(0)], lap=total_laps - 1)
    assert not is_finished(state)
    state = _state([_car(0)], lap=total_laps)
    assert is_finished(state)


def test_full_race_completes_via_repeated_steps() -> None:
    total_laps = TRACKS["silverstone"]["laps"]
    state = _state([_car(0), _car(1)])
    while not is_finished(state):
        state, _trace, _events = step(state, None, seed=state.seed)
    assert state.lap == total_laps


def test_step_freezes_retired_car() -> None:
    state = _state([_car(0, tyre_age=10, total_time=500.0, retired_lap=5)])
    new_state, trace, _events = step(state, None, seed=state.seed)
    assert new_state.cars[0].total_time == 500.0
    assert new_state.cars[0].tyre_age == 10
    assert new_state.cars[0].retired_lap == 5
    assert trace.cars[0].lap_time == 0.0
    assert trace.cars[0].total_time == 500.0


def test_step_damaged_car_is_slower_than_undamaged() -> None:
    clean = _state([_car(0, damage=0)])
    damaged = _state([_car(0, damage=2)])
    _clean_state, clean_trace, _e1 = step(clean, None, seed=clean.seed)
    _damaged_state, damaged_trace, _e2 = step(damaged, None, seed=damaged.seed)
    assert damaged_trace.cars[0].lap_time > clean_trace.cars[0].lap_time


def test_step_ranks_retirees_behind_active_cars_by_retired_lap() -> None:
    state = _state(
        [
            _car(0, total_time=1000.0),  # active, slow total_time
            _car(1, total_time=10.0),  # active, fast total_time
            _car(2, retired_lap=10),  # retired earlier
            _car(3, retired_lap=30),  # retired later - should rank ahead of car 2
        ]
    )
    _new_state, trace, _events = step(state, None, seed=state.seed)
    by_id = {c.id: c.position for c in trace.cars}
    assert by_id[1] < by_id[0] < by_id[3] < by_id[2]
