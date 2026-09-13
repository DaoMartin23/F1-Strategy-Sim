from api.schemas import (
    CarLapModel,
    CarStateModel,
    DecisionModel,
    EventModel,
    LapTraceModel,
    StateModel,
)
from sim.race import new_race
from sim.types import Compound, EventType


def test_state_model_validates_from_a_real_state() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    model = StateModel.model_validate(state, from_attributes=True)
    assert model.track == "silverstone"
    assert model.seed == 1
    assert model.starting_position == 10
    assert len(model.cars) == 20
    assert model.cars[0].id == 0
    assert model.cars[0].car == "car_5"


def test_car_state_model_serializes_compound_as_string() -> None:
    model = CarStateModel(
        id=0,
        car="car_5",
        compound=Compound.MEDIUM,
        tyre_age=5,
        pit_count=0,
        damage=0,
        total_time=100.0,
    )
    dumped = model.model_dump()
    assert dumped["compound"] == "M"


def test_event_model_serializes_event_type_as_string() -> None:
    model = EventModel(type=EventType.SAFETY_CAR, lap=10, options=["hold_position"], context={})
    dumped = model.model_dump()
    assert dumped["type"] == "safety_car"


def test_decision_model_defaults() -> None:
    model = DecisionModel()
    assert model.choice is None
    assert model.push is None


def test_car_lap_and_lap_trace_model_construction() -> None:
    car_lap = CarLapModel(id=0, position=1, total_time=90.0, lap_time=90.0, compound=Compound.SOFT, tyre_age=1)
    trace = LapTraceModel(lap=1, wetness=0.0, cars=[car_lap])
    assert trace.cars[0].compound == Compound.SOFT
