import dataclasses

from sim.model import PARAMS, TRACKS, lap_time, pit_loss
from sim.rng import PURPOSE_NOISE, PURPOSE_PIT_LOSS, make_rng
from sim.types import CarLap, CarState, Compound, Decision, Event, LapTrace, State

_PIT_CHOICES: dict[str, Compound] = {
    "pit_soft": Compound.SOFT,
    "pit_medium": Compound.MEDIUM,
    "pit_hard": Compound.HARD,
    "pit_inter": Compound.INTER,
    "pit_wet": Compound.WET,
}


def is_finished(state: State) -> bool:
    return state.lap >= TRACKS[state.track]["laps"]


def _apply_pit(car: CarState, compound: Compound, seed: int, lap_number: int) -> CarState:
    rng = make_rng(seed, lap_number, PURPOSE_PIT_LOSS, car.id)
    return dataclasses.replace(
        car,
        compound=compound,
        tyre_age=0,
        pit_count=car.pit_count + 1,
        total_time=car.total_time + pit_loss(rng),
    )


def step(state: State, decision: Decision | None, seed: int) -> tuple[State, LapTrace, list[Event]]:
    lap_number = state.lap + 1
    push_active = state.push_active
    cars = list(state.cars)

    if decision is not None:
        if decision.push is not None:
            push_active = decision.push
        if decision.choice in _PIT_CHOICES and cars:
            compound = _PIT_CHOICES[decision.choice]
            cars[0] = _apply_pit(cars[0], compound, seed, lap_number)

    new_cars: list[CarState] = []
    lap_entries: list[CarLap] = []
    for car in cars:
        pushing = push_active and car.id == 0
        extra_wear = 1 + PARAMS["push_extra_wear"] if pushing else 1
        new_tyre_age = car.tyre_age + extra_wear

        noise_rng = make_rng(seed, lap_number, PURPOSE_NOISE, car.id)
        this_lap_time = lap_time(car.car, state.track, lap_number, car.compound, new_tyre_age, 0.0, noise_rng)
        if pushing:
            this_lap_time -= PARAMS["push_time_gain"]

        new_total_time = car.total_time + this_lap_time
        new_car = dataclasses.replace(car, tyre_age=new_tyre_age, total_time=new_total_time)
        new_cars.append(new_car)
        lap_entries.append(
            CarLap(
                id=car.id,
                position=0,
                total_time=new_total_time,
                lap_time=this_lap_time,
                compound=new_car.compound,
                tyre_age=new_car.tyre_age,
            )
        )

    ranked = sorted(lap_entries, key=lambda entry: entry.total_time)
    position_by_id = {entry.id: idx + 1 for idx, entry in enumerate(ranked)}
    lap_entries = [dataclasses.replace(entry, position=position_by_id[entry.id]) for entry in lap_entries]

    new_state = dataclasses.replace(
        state,
        lap=lap_number,
        cars=new_cars,
        push_active=push_active,
        pending_decision=None,
    )
    trace = LapTrace(lap=lap_number, wetness=0.0, cars=lap_entries)
    return new_state, trace, []
