from dataclasses import dataclass
from enum import Enum


class Compound(str, Enum):
    SOFT = "S"
    MEDIUM = "M"
    HARD = "H"
    INTER = "I"
    WET = "W"


class EventType(str, Enum):
    RAIN_START = "rain_start"
    RAIN_END = "rain_end"
    DAMAGE = "damage"
    OVERTAKEN = "overtaken"
    SAFETY_CAR = "safety_car"
    PIT_OPPORTUNITY = "pitting_opportunity"


@dataclass(frozen=True)
class CarState:
    id: int
    car: str
    compound: Compound
    tyre_age: int
    pit_count: int
    damage: int
    total_time: float
    retired_lap: int | None = None


@dataclass(frozen=True)
class CarLap:
    id: int
    position: int
    total_time: float
    lap_time: float
    compound: Compound
    tyre_age: int


@dataclass(frozen=True)
class LapTrace:
    lap: int
    wetness: float
    cars: list[CarLap]


@dataclass(frozen=True)
class PitPlanEntry:
    target_lap: int
    compound: Compound


@dataclass(frozen=True)
class DecisionLogEntry:
    lap: int
    event_type: EventType
    choice: str
    delta_seconds: float


@dataclass(frozen=True)
class Event:
    type: EventType
    lap: int
    options: list[str]
    context: dict[str, object]


@dataclass(frozen=True)
class Decision:
    choice: str | None = None
    push: bool | None = None


@dataclass(frozen=True)
class State:
    track: str
    seed: int
    lap: int
    push_active: bool
    starting_position: int
    player_strategy: list[PitPlanEntry]
    pending_decision: Event | None
    decision_log: list[DecisionLogEntry]
    cars: list[CarState]
