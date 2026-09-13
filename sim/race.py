import dataclasses
from enum import Enum

from sim.model import CAR_CHOICES, PARAMS, TRACKS, lap_time, pit_loss
from sim.rng import PURPOSE_GRID, PURPOSE_NOISE, PURPOSE_PIT_LOSS, make_rng
from sim.types import CarLap, CarState, Compound, Decision, Event, LapTrace, PitPlanEntry, State

_PIT_CHOICES: dict[str, Compound] = {
    "pit_soft": Compound.SOFT,
    "pit_medium": Compound.MEDIUM,
    "pit_hard": Compound.HARD,
    "pit_inter": Compound.INTER,
    "pit_wet": Compound.WET,
}


class RivalTemplate(str, Enum):
    ONE_STOP = "one_stop"
    TWO_STOP = "two_stop"


def _rival_car_choice(car_id: int) -> str:
    keys = list(CAR_CHOICES.keys())
    return keys[(car_id - 1) % len(keys)]


def _compute_grid(starting_position: int, cars: list[CarState], seed: int) -> dict[int, int]:
    rivals = [car for car in cars if car.id != 0]
    grid_rng = make_rng(seed, 0, PURPOSE_GRID)
    jittered_pace = {
        car.id: CAR_CHOICES[car.car] + grid_rng.normal(0.0, PARAMS["grid_shuffle_std"]) for car in rivals
    }
    ranked_rivals = sorted(rivals, key=lambda car: jittered_pace[car.id])
    grid: dict[int, int] = {0: starting_position}
    rival_iter = iter(ranked_rivals)
    for slot in range(1, len(cars) + 1):
        if slot == starting_position:
            continue
        grid[next(rival_iter).id] = slot
    return grid


def _rival_template(pace_offset: float, grid_slot: int) -> RivalTemplate:
    if pace_offset <= 0.0 or grid_slot >= 15:
        return RivalTemplate.TWO_STOP
    return RivalTemplate.ONE_STOP


def rival_plan(car_id: int, template: RivalTemplate, total_laps: int) -> list[PitPlanEntry]:
    if template is RivalTemplate.ONE_STOP:
        target = round(total_laps * 0.45) + (car_id % 5)
        return [PitPlanEntry(target_lap=target, compound=Compound.HARD)]
    first = round(total_laps * 0.30) + (car_id % 3)
    second = round(total_laps * 0.65) + (car_id % 3)
    return [
        PitPlanEntry(target_lap=first, compound=Compound.MEDIUM),
        PitPlanEntry(target_lap=second, compound=Compound.HARD),
    ]


def new_race(track: str, seed: int, player_car: str, starting_position: int) -> State:
    total_laps = TRACKS[track]["laps"]
    cars = [
        CarState(id=0, car=player_car, compound=Compound.MEDIUM, tyre_age=0, pit_count=0, damage=0, total_time=0.0)
    ]
    for car_id in range(1, 20):
        cars.append(
            CarState(
                id=car_id,
                car=_rival_car_choice(car_id),
                compound=Compound.MEDIUM,
                tyre_age=0,
                pit_count=0,
                damage=0,
                total_time=0.0,
            )
        )
    return State(
        track=track,
        seed=seed,
        lap=0,
        push_active=False,
        starting_position=starting_position,
        player_strategy=rival_plan(0, RivalTemplate.ONE_STOP, total_laps),
        pending_decision=None,
        decision_log=[],
        cars=cars,
    )


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


def _retired_lap_or_raise(car: CarState) -> int:
    assert car.retired_lap is not None
    return car.retired_lap


def step(state: State, decision: Decision | None, seed: int) -> tuple[State, LapTrace, list[Event]]:
    lap_number = state.lap + 1
    push_active = state.push_active
    cars = list(state.cars)
    total_laps = TRACKS[state.track]["laps"]

    if decision is not None:
        if decision.push is not None:
            push_active = decision.push
        if decision.choice in _PIT_CHOICES and cars and cars[0].retired_lap is None:
            compound = _PIT_CHOICES[decision.choice]
            cars[0] = _apply_pit(cars[0], compound, seed, lap_number)

    grid = _compute_grid(state.starting_position, cars, seed)
    for idx, car in enumerate(cars):
        if car.id == 0 or car.retired_lap is not None:
            continue
        pace_offset = CAR_CHOICES[car.car]
        template = _rival_template(pace_offset, grid[car.id])
        plan = rival_plan(car.id, template, total_laps)
        for plan_entry in plan:
            if plan_entry.target_lap == lap_number:
                cars[idx] = _apply_pit(cars[idx], plan_entry.compound, seed, lap_number)
                break

    new_cars: list[CarState] = []
    paired: list[tuple[CarState, CarLap]] = []
    for car in cars:
        if car.retired_lap is not None:
            new_car = car
            entry = CarLap(
                id=car.id,
                position=0,
                total_time=car.total_time,
                lap_time=0.0,
                compound=car.compound,
                tyre_age=car.tyre_age,
            )
        else:
            pushing = push_active and car.id == 0
            extra_wear = 1 + PARAMS["push_extra_wear"] if pushing else 1
            new_tyre_age = car.tyre_age + extra_wear

            noise_rng = make_rng(seed, lap_number, PURPOSE_NOISE, car.id)
            this_lap_time = lap_time(
                car.car, state.track, lap_number, car.compound, new_tyre_age, 0.0, noise_rng, car.damage
            )
            if pushing:
                this_lap_time -= PARAMS["push_time_gain"]

            new_total_time = car.total_time + this_lap_time
            new_car = dataclasses.replace(car, tyre_age=new_tyre_age, total_time=new_total_time)
            entry = CarLap(
                id=car.id,
                position=0,
                total_time=new_total_time,
                lap_time=this_lap_time,
                compound=new_car.compound,
                tyre_age=new_car.tyre_age,
            )
        new_cars.append(new_car)
        paired.append((new_car, entry))

    active_pairs = [pair for pair in paired if pair[0].retired_lap is None]
    retired_pairs = [pair for pair in paired if pair[0].retired_lap is not None]
    active_pairs.sort(key=lambda pair: pair[1].total_time)
    retired_pairs.sort(key=lambda pair: -_retired_lap_or_raise(pair[0]))
    ordered = active_pairs + retired_pairs
    lap_entries = [dataclasses.replace(entry, position=idx + 1) for idx, (_car, entry) in enumerate(ordered)]

    new_state = dataclasses.replace(
        state,
        lap=lap_number,
        cars=new_cars,
        push_active=push_active,
        pending_decision=None,
    )
    trace = LapTrace(lap=lap_number, wetness=0.0, cars=lap_entries)
    return new_state, trace, []
