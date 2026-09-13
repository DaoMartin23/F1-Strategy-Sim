import dataclasses
import json

import pytest

from sim.types import (
    CarLap,
    CarState,
    Compound,
    Decision,
    DecisionLogEntry,
    Event,
    EventType,
    LapTrace,
    PitPlanEntry,
    State,
)


def _sample_car(car_id: int) -> CarState:
    return CarState(
        id=car_id,
        car="alpha",
        compound=Compound.MEDIUM,
        tyre_age=12,
        pit_count=1,
        damage=0,
        total_time=1234.567,
    )


def test_car_state_fields() -> None:
    car = _sample_car(0)
    assert car.id == 0
    assert car.compound is Compound.MEDIUM


def test_dataclasses_are_frozen() -> None:
    car = _sample_car(0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        car.tyre_age = 99  # type: ignore[misc]


def test_event_and_decision_construction() -> None:
    event = Event(
        type=EventType.PIT_OPPORTUNITY,
        lap=20,
        options=["pit_soft", "pit_medium", "pit_hard", "stay_out"],
        context={"rivals_pitted": [3, 7, 11]},
    )
    decision = Decision(choice="pit_medium", push=None)
    assert event.type is EventType.PIT_OPPORTUNITY
    assert decision.choice == "pit_medium"


def _sample_state() -> State:
    cars = [_sample_car(i) for i in range(20)]
    log = [
        DecisionLogEntry(lap=5, event_type=EventType.SAFETY_CAR, choice="pit_medium", delta_seconds=-8.4),
        DecisionLogEntry(lap=18, event_type=EventType.OVERTAKEN, choice="push", delta_seconds=2.1),
        DecisionLogEntry(lap=33, event_type=EventType.RAIN_START, choice="inter", delta_seconds=-5.0),
    ]
    pending = Event(
        type=EventType.PIT_OPPORTUNITY,
        lap=40,
        options=["pit_soft", "pit_medium", "pit_hard", "stay_out"],
        context={"rivals_pitted": [2, 9]},
    )
    return State(
        track="silverstone",
        seed=12345,
        lap=40,
        push_active=False,
        starting_position=10,
        player_strategy=[
            PitPlanEntry(target_lap=18, compound=Compound.MEDIUM),
            PitPlanEntry(target_lap=38, compound=Compound.HARD),
        ],
        pending_decision=pending,
        decision_log=log,
        cars=cars,
    )


def test_state_has_twenty_cars() -> None:
    state = _sample_state()
    assert len(state.cars) == 20
    assert state.cars[0].id == 0


def test_state_serializes_under_5kb() -> None:
    state = _sample_state()
    payload = json.dumps(dataclasses.asdict(state))
    assert len(payload.encode("utf-8")) < 5000


def test_state_worst_case_still_under_5kb() -> None:
    """Stress case: more decision-log entries and a populated pending_decision context."""
    state = _sample_state()
    heavy_log = [
        DecisionLogEntry(lap=lap, event_type=EventType.PIT_OPPORTUNITY, choice="pit_medium", delta_seconds=-3.2)
        for lap in range(5, 50, 5)
    ]
    assert state.pending_decision is not None
    heavy_pending = dataclasses.replace(
        state.pending_decision,
        context={"rivals_pitted": list(range(1, 15))},
    )
    heavy_state = dataclasses.replace(state, decision_log=heavy_log, pending_decision=heavy_pending)
    payload = json.dumps(dataclasses.asdict(heavy_state))
    assert len(payload.encode("utf-8")) < 5000


def test_state_with_no_pending_decision() -> None:
    state = dataclasses.replace(_sample_state(), pending_decision=None)
    payload = json.dumps(dataclasses.asdict(state))
    assert len(payload.encode("utf-8")) < 5000


def test_lap_trace_construction() -> None:
    trace = LapTrace(
        lap=12,
        wetness=0.0,
        cars=[
            CarLap(
                id=i,
                position=i + 1,
                total_time=100.0 * (i + 1),
                lap_time=91.2,
                compound=Compound.MEDIUM,
                tyre_age=12,
            )
            for i in range(20)
        ],
    )
    assert len(trace.cars) == 20
    assert trace.cars[0].position == 1
