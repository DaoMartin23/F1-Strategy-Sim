from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from api.schemas import (
    DecisionModel,
    EventModel,
    LapTraceModel,
    StateModel,
    decision_from_model,
    state_from_model,
)
from sim.model import CAR_CHOICES, TRACKS
from sim.race import new_race, run_to_next_decision

router = APIRouter(prefix="/race", tags=["race"])


class NewRaceRequest(BaseModel):
    track: str
    seed: int
    car: str
    starting_position: int = Field(ge=1, le=20)

    @field_validator("track")
    @classmethod
    def track_must_be_known(cls, value: str) -> str:
        if value not in TRACKS:
            raise ValueError(f"unknown track: {value}")
        return value

    @field_validator("car")
    @classmethod
    def car_must_be_known(cls, value: str) -> str:
        if value not in CAR_CHOICES:
            raise ValueError(f"unknown car: {value}")
        return value


@router.post("/new", response_model=StateModel)
def create_race(request: NewRaceRequest) -> StateModel:
    state = new_race(request.track, request.seed, request.car, request.starting_position)
    return StateModel.model_validate(state, from_attributes=True)


class StepRequest(BaseModel):
    state: StateModel
    decision: DecisionModel | None = None


class StepResponse(BaseModel):
    state: StateModel
    laps: list[LapTraceModel]
    event: EventModel | None


@router.post("/step", response_model=StepResponse)
def step_race(request: StepRequest) -> StepResponse:
    state = state_from_model(request.state)
    decision = decision_from_model(request.decision) if request.decision is not None else None
    new_state, laps, event = run_to_next_decision(state, decision, seed=state.seed)
    return StepResponse(
        state=StateModel.model_validate(new_state, from_attributes=True),
        laps=[LapTraceModel.model_validate(lap, from_attributes=True) for lap in laps],
        event=EventModel.model_validate(event, from_attributes=True) if event is not None else None,
    )
