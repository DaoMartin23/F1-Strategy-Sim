from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from api.schemas import StateModel
from sim.model import CAR_CHOICES, TRACKS
from sim.race import new_race

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
