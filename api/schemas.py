from pydantic import BaseModel

from sim.types import Compound, EventType


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
