import pytest

from sim.model import PARAMS
from sim.race import is_finished, new_race, step
from sim.types import CarState, Compound, Decision, EventType, State


def _car(
    car_id: int,
    car: str = "car_1",
    tyre_age: int = 5,
    total_time: float = 0.0,
) -> CarState:
    return CarState(
        id=car_id,
        car=car,
        compound=Compound.MEDIUM,
        tyre_age=tyre_age,
        pit_count=0,
        damage=0,
        total_time=total_time,
    )


def _state(cars: list[CarState], **kwargs: object) -> State:
    defaults: dict[str, object] = dict(
        track="silverstone",
        seed=123,
        lap=0,
        push_active=False,
        starting_position=1,
        player_strategy=[],
        pending_decision=None,
        decision_log=[],
        cars=cars,
        safety_car_ends_after_lap=None,
    )
    defaults.update(kwargs)
    return State(**defaults)  # type: ignore[arg-type]


def test_full_sc_lap_is_exactly_120_seconds_for_every_car() -> None:
    state = _state([_car(0), _car(1)], safety_car_ends_after_lap=1)
    _new_state, trace, _events = step(state, None, seed=state.seed)
    sc_pace = PARAMS["safety_car"]["lap_time_seconds"]
    for car_lap in trace.cars:
        assert car_lap.lap_time == pytest.approx(sc_pace)


def test_sc_period_clears_after_the_full_caution_lap() -> None:
    state = _state([_car(0), _car(1)], safety_car_ends_after_lap=1)
    new_state, _trace, _events = step(state, None, seed=state.seed)
    assert new_state.safety_car_ends_after_lap is None


def test_pitting_during_full_sc_lap_still_pays_pit_loss() -> None:
    state = _state([_car(0, tyre_age=20)], safety_car_ends_after_lap=1)
    no_pit_state, no_pit_trace, _e1 = step(state, None, seed=state.seed)
    pit_state, _pit_trace, _e2 = step(state, Decision(choice="pit_hard"), seed=state.seed)

    sc_pace = PARAMS["safety_car"]["lap_time_seconds"]
    assert no_pit_trace.cars[0].lap_time == pytest.approx(sc_pace)

    pit_delta = pit_state.cars[0].total_time - state.cars[0].total_time
    no_pit_delta = no_pit_state.cars[0].total_time - state.cars[0].total_time
    # Same margin technique as the Stage 4 pit-cost test: pit_loss (>=18s)
    # dwarfs any other small difference between the two runs.
    assert pit_delta - no_pit_delta > 15.0


def test_push_adds_no_extra_tyre_wear_during_full_sc_lap() -> None:
    state = _state([_car(0, tyre_age=5)], safety_car_ends_after_lap=1)
    new_state, _trace, _events = step(state, Decision(push=True), seed=state.seed)
    assert new_state.cars[0].tyre_age == 6


def test_overtaken_never_fires_during_full_sc_lap() -> None:
    # Same setup as the Stage 6e overtaken test (a ~1.3s/lap pace gap that
    # reliably produces a crossing under normal racing) but with a safety
    # car forced active - this must NOT fire an overtake.
    state = _state(
        [_car(0, car="car_10", total_time=50.0), _car(1, car="car_1", total_time=51.0)],
        safety_car_ends_after_lap=1,
    )
    _new_state, _trace, events = step(state, None, seed=state.seed)
    assert not any(e.type is EventType.OVERTAKEN for e in events)


def test_overtaking_resumes_once_sc_period_clears() -> None:
    state = _state(
        [_car(0, car="car_10", total_time=50.0), _car(1, car="car_1", total_time=51.0)],
        safety_car_ends_after_lap=1,
    )
    sc_state, _trace, sc_events = step(state, None, seed=state.seed)
    assert not any(e.type is EventType.OVERTAKEN for e in sc_events)
    assert sc_state.safety_car_ends_after_lap is None

    resumed_state, _trace2, resumed_events = step(sc_state, None, seed=sc_state.seed)
    assert any(e.type is EventType.OVERTAKEN for e in resumed_events)


def test_step_trigger_lap_is_blended_and_next_lap_is_full_sc_pace() -> None:
    # No forced fixture here: search real races for a naturally-occurring
    # safety_car event, then verify the trigger lap's time is strictly
    # faster than full SC pace (proving it's blended, not just capped) and
    # that the very next lap runs at exactly SC pace for the player.
    track = "silverstone"
    sc_pace = PARAMS["safety_car"]["lap_time_seconds"]
    trigger_state = None
    trigger_trace = None
    for seed in range(300):
        candidate_state = new_race(track, seed=seed, player_car="car_5", starting_position=10)
        found = False
        while not is_finished(candidate_state):
            candidate_state, candidate_trace, events = step(candidate_state, None, seed=candidate_state.seed)
            if any(e.type is EventType.SAFETY_CAR for e in events):
                trigger_state, trigger_trace = candidate_state, candidate_trace
                found = True
                break
        if found:
            break
    assert trigger_state is not None and trigger_trace is not None

    player_trigger_lap_time = next(c.lap_time for c in trigger_trace.cars if c.id == 0)
    assert player_trigger_lap_time < sc_pace - 1.0
    assert trigger_state.safety_car_ends_after_lap == trigger_state.lap + 1

    next_state, next_trace, _events = step(trigger_state, None, seed=trigger_state.seed)
    assert next_state.safety_car_ends_after_lap is None
    if next_state.cars[0].retired_lap is None:
        player_next_lap_time = next(c.lap_time for c in next_trace.cars if c.id == 0)
        assert player_next_lap_time == pytest.approx(sc_pace)
