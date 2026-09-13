from pydantic import BaseModel

from sim.types import (
    CarState,
    Compound,
    Decision,
    DecisionLogEntry,
    Event,
    EventType,
    PitPlanEntry,
    State,
)


class CarStateModel(BaseModel):
    id: int
    car: str
    compound: Compound
    tyre_age: int
    pit_count: int
    damage: int
    total_time: float
    retired_lap: int | None = None


class CarLapModel(BaseModel):
    id: int
    position: int
    total_time: float
    lap_time: float
    compound: Compound
    tyre_age: int


class LapTraceModel(BaseModel):
    lap: int
    wetness: float
    cars: list[CarLapModel]


class PitPlanEntryModel(BaseModel):
    target_lap: int
    compound: Compound


class DecisionLogEntryModel(BaseModel):
    lap: int
    event_type: EventType
    choice: str
    delta_seconds: float


class EventModel(BaseModel):
    type: EventType
    lap: int
    options: list[str]
    context: dict[str, object]


class DecisionModel(BaseModel):
    choice: str | None = None
    push: bool | None = None


class StateModel(BaseModel):
    track: str
    seed: int
    lap: int
    push_active: bool
    starting_position: int
    player_strategy: list[PitPlanEntryModel]
    pending_decision: EventModel | None
    decision_log: list[DecisionLogEntryModel]
    cars: list[CarStateModel]
    safety_car_ends_after_lap: int | None = None


def car_state_from_model(model: CarStateModel) -> CarState:
    return CarState(
        id=model.id,
        car=model.car,
        compound=model.compound,
        tyre_age=model.tyre_age,
        pit_count=model.pit_count,
        damage=model.damage,
        total_time=model.total_time,
        retired_lap=model.retired_lap,
    )


def pit_plan_entry_from_model(model: PitPlanEntryModel) -> PitPlanEntry:
    return PitPlanEntry(target_lap=model.target_lap, compound=model.compound)


def decision_log_entry_from_model(model: DecisionLogEntryModel) -> DecisionLogEntry:
    return DecisionLogEntry(
        lap=model.lap, event_type=model.event_type, choice=model.choice, delta_seconds=model.delta_seconds
    )


def event_from_model(model: EventModel) -> Event:
    return Event(type=model.type, lap=model.lap, options=list(model.options), context=dict(model.context))


def decision_from_model(model: DecisionModel) -> Decision:
    return Decision(choice=model.choice, push=model.push)


def state_from_model(model: StateModel) -> State:
    return State(
        track=model.track,
        seed=model.seed,
        lap=model.lap,
        push_active=model.push_active,
        starting_position=model.starting_position,
        player_strategy=[pit_plan_entry_from_model(entry) for entry in model.player_strategy],
        pending_decision=event_from_model(model.pending_decision) if model.pending_decision is not None else None,
        decision_log=[decision_log_entry_from_model(entry) for entry in model.decision_log],
        cars=[car_state_from_model(car) for car in model.cars],
        safety_car_ends_after_lap=model.safety_car_ends_after_lap,
    )
