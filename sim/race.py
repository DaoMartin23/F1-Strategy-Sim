import dataclasses
from enum import Enum

import numpy as np

from sim.model import CAR_CHOICES, PARAMS, TRACKS, incident_chance, lap_time, pit_loss, safety_car_chance, weather_at
from sim.rng import (
    PURPOSE_DAMAGE_CHANCE,
    PURPOSE_GRID,
    PURPOSE_NOISE,
    PURPOSE_PIT_LOSS,
    PURPOSE_SAFETY_CAR_TRIGGER,
    make_rng,
)
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


def detect_rain_start(prev_wetness: float, wetness: float, lap: int) -> Event | None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    if prev_wetness < threshold <= wetness:
        return Event(
            type=EventType.RAIN_START,
            lap=lap,
            options=["stay_out", "pit_inter", "pit_wet"],
            context={"wetness": wetness},
        )
    return None


def detect_rain_end(prev_wetness: float, wetness: float, lap: int) -> Event | None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    if prev_wetness >= threshold > wetness:
        return Event(
            type=EventType.RAIN_END,
            lap=lap,
            options=["pit_soft", "pit_medium", "pit_hard", "stay_out"],
            context={"wetness": wetness},
        )
    return None


def detect_safety_car(incident_occurred: bool, rng: np.random.Generator, lap: int) -> Event | None:
    if rng.random() < safety_car_chance(incident_occurred):
        return Event(
            type=EventType.SAFETY_CAR,
            lap=lap,
            options=["pit_soft", "pit_medium", "pit_hard", "hold_position"],
            context={},
        )
    return None


def detect_overtaken(
    prev_cars: list[CarState], new_cars: list[CarState], player_pitted: bool, lap: int
) -> Event | None:
    if player_pitted:
        return None
    prev_player = next(c for c in prev_cars if c.id == 0)
    new_player = next(c for c in new_cars if c.id == 0)
    if new_player.retired_lap is not None:
        return None
    for prev_car, new_car in zip(prev_cars, new_cars):
        if prev_car.id == 0 or new_car.retired_lap is not None:
            continue
        if prev_car.total_time > prev_player.total_time and new_car.total_time < new_player.total_time:
            return Event(
                type=EventType.OVERTAKEN,
                lap=lap,
                options=["push", "hold_position"],
                context={"overtaken_by": new_car.id},
            )
    return None


def detect_pitting_opportunity(
    player: CarState, rivals: list[CarState], player_strategy: list[PitPlanEntry], lap: int
) -> Event | None:
    near_target = False
    if player.pit_count == 0:
        near_target = any(abs(entry.target_lap - lap) <= 1 for entry in player_strategy)
    cliff_lap = PARAMS["tyre"][player.compound]["cliff_lap"]
    past_cliff = player.tyre_age > cliff_lap
    if not (near_target or past_cliff):
        return None
    rivals_pitted = [rival.id for rival in rivals if rival.pit_count > 0 and rival.retired_lap is None]
    return Event(
        type=EventType.PIT_OPPORTUNITY,
        lap=lap,
        options=["pit_soft", "pit_medium", "pit_hard", "stay_out"],
        context={"rivals_pitted": rivals_pitted},
    )


def _apply_pit(car: CarState, compound: Compound, seed: int, lap_number: int) -> CarState:
    rng = make_rng(seed, lap_number, PURPOSE_PIT_LOSS, car.id)
    return dataclasses.replace(
        car,
        compound=compound,
        tyre_age=0,
        pit_count=car.pit_count + 1,
        total_time=car.total_time + pit_loss(rng),
    )


def _apply_repair(car: CarState, seed: int, lap_number: int) -> CarState:
    rng = make_rng(seed, lap_number, PURPOSE_PIT_LOSS, car.id)
    extra = PARAMS["incident"]["repair_extra_time"]
    return dataclasses.replace(
        car,
        tyre_age=0,
        damage=0,
        pit_count=car.pit_count + 1,
        total_time=car.total_time + pit_loss(rng) + extra,
    )


def _roll_incidents(
    cars: list[CarState], wetness: float, push_active: bool, seed: int, lap_number: int
) -> tuple[list[CarState], bool, Event | None]:
    updated: list[CarState] = []
    incident_occurred = False
    player_damage_event: Event | None = None
    for car in cars:
        if car.retired_lap is not None:
            updated.append(car)
            continue
        pushing = push_active and car.id == 0
        rng = make_rng(seed, lap_number, PURPOSE_DAMAGE_CHANCE, car.id)
        chance = incident_chance(car.compound, wetness, pushing)
        if rng.random() < chance:
            incident_occurred = True
            if rng.random() < PARAMS["incident"]["dnf_given_incident_probability"]:
                car = dataclasses.replace(car, retired_lap=lap_number)
            else:
                car = dataclasses.replace(car, damage=min(2, car.damage + 1))
                if car.id == 0:
                    player_damage_event = Event(
                        type=EventType.DAMAGE,
                        lap=lap_number,
                        options=["repair", "stay_out"],
                        context={"damage": car.damage},
                    )
        updated.append(car)
    return updated, incident_occurred, player_damage_event


def _retired_lap_or_raise(car: CarState) -> int:
    assert car.retired_lap is not None
    return car.retired_lap


def step(state: State, decision: Decision | None, seed: int) -> tuple[State, LapTrace, list[Event]]:
    lap_number = state.lap + 1
    push_active = state.push_active
    cars = list(state.cars)
    total_laps = TRACKS[state.track]["laps"]

    player_pitted = False
    if decision is not None:
        if decision.push is not None:
            push_active = decision.push
        if decision.choice == "push":
            push_active = True
        elif decision.choice == "hold_position":
            push_active = False
        if decision.choice in _PIT_CHOICES and cars and cars[0].retired_lap is None:
            compound = _PIT_CHOICES[decision.choice]
            cars[0] = _apply_pit(cars[0], compound, seed, lap_number)
            player_pitted = True
        elif decision.choice == "repair" and cars and cars[0].retired_lap is None:
            cars[0] = _apply_repair(cars[0], seed, lap_number)
            player_pitted = True

    prev_wetness = weather_at(seed, state.track, state.lap)
    wetness = weather_at(seed, state.track, lap_number)
    events: list[Event] = []
    rain_start_event = detect_rain_start(prev_wetness, wetness, lap_number)
    if rain_start_event is not None:
        events.append(rain_start_event)
    rain_end_event = detect_rain_end(prev_wetness, wetness, lap_number)
    if rain_end_event is not None:
        events.append(rain_end_event)

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

    cars, incident_occurred, player_damage_event = _roll_incidents(cars, wetness, push_active, seed, lap_number)
    if player_damage_event is not None:
        events.append(player_damage_event)

    sc_normal_fraction: float | None = None
    new_sc_ends_after_lap = state.safety_car_ends_after_lap
    if state.safety_car_ends_after_lap is not None and lap_number == state.safety_car_ends_after_lap:
        # The full caution lap: everyone runs entirely at SC pace.
        sc_normal_fraction = 0.0
        new_sc_ends_after_lap = None
    elif state.safety_car_ends_after_lap is None:
        safety_car_rng = make_rng(seed, lap_number, PURPOSE_SAFETY_CAR_TRIGGER)
        safety_car_event = detect_safety_car(incident_occurred, safety_car_rng, lap_number)
        if safety_car_event is not None:
            events.append(safety_car_event)
            # Second draw off the same generator: how far through this lap
            # normal racing happened before the SC came out.
            sc_normal_fraction = float(safety_car_rng.random())
            new_sc_ends_after_lap = lap_number + 1

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
            sc_affected = sc_normal_fraction is not None
            pushing = push_active and car.id == 0
            # Push's time benefit is left to naturally diminish via the SC
            # blend below (zero weight on the full-caution lap, partial
            # weight on the trigger lap's pre-SC portion); its tyre-wear
            # side effect is explicitly skipped for any SC-affected lap -
            # you're not really pushing hard while bunched up under caution.
            extra_wear = 1 + PARAMS["push_extra_wear"] if (pushing and not sc_affected) else 1
            new_tyre_age = car.tyre_age + extra_wear

            noise_rng = make_rng(seed, lap_number, PURPOSE_NOISE, car.id)
            this_lap_time = lap_time(
                car.car, state.track, lap_number, car.compound, new_tyre_age, wetness, noise_rng, car.damage
            )
            if pushing:
                this_lap_time -= PARAMS["push_time_gain"]
            if sc_normal_fraction is not None:
                sc_pace = PARAMS["safety_car"]["lap_time_seconds"]
                this_lap_time = sc_normal_fraction * this_lap_time + (1 - sc_normal_fraction) * sc_pace

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

    if sc_normal_fraction is None:
        overtaken_event = detect_overtaken(state.cars, new_cars, player_pitted, lap_number)
        if overtaken_event is not None:
            events.append(overtaken_event)

    if new_cars and new_cars[0].retired_lap is None:
        pitting_event = detect_pitting_opportunity(new_cars[0], new_cars[1:], state.player_strategy, lap_number)
        if pitting_event is not None:
            events.append(pitting_event)

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
        safety_car_ends_after_lap=new_sc_ends_after_lap,
    )
    trace = LapTrace(lap=lap_number, wetness=wetness, cars=lap_entries)
    return new_state, trace, events


EVENT_PRIORITY: list[EventType] = [
    EventType.DAMAGE,
    EventType.SAFETY_CAR,
    EventType.RAIN_START,
    EventType.RAIN_END,
    EventType.OVERTAKEN,
    EventType.PIT_OPPORTUNITY,
]


def _pick_priority_event(events: list[Event]) -> Event:
    for event_type in EVENT_PRIORITY:
        for event in events:
            if event.type is event_type:
                return event
    return events[0]


_NO_ACTION_CHOICES = {"stay_out", "hold_position"}


def _alternative_choice(event: Event, chosen: str) -> str:
    if chosen in _NO_ACTION_CHOICES:
        for option in event.options:
            if option not in _NO_ACTION_CHOICES:
                return option
        return chosen
    for option in event.options:
        if option in _NO_ACTION_CHOICES:
            return option
    return chosen


def run_to_next_decision(
    state: State, decision: Decision | None, seed: int
) -> tuple[State, list[LapTrace], Event | None]:
    laps: list[LapTrace] = []
    current_decision = decision
    pending_log_alt_time: float | None = None
    pending_log_event: Event | None = None
    pending_log_choice: str | None = None

    if decision is not None and decision.choice is not None and state.pending_decision is not None:
        event = state.pending_decision
        alternative = _alternative_choice(event, decision.choice)
        alt_state, _alt_trace, _alt_events = step(state, Decision(choice=alternative), seed)
        pending_log_alt_time = alt_state.cars[0].total_time
        pending_log_event = event
        pending_log_choice = decision.choice

    while not is_finished(state):
        state, trace, events = step(state, current_decision, seed)
        laps.append(trace)
        current_decision = None

        if pending_log_event is not None and pending_log_alt_time is not None and pending_log_choice is not None:
            chosen_time = state.cars[0].total_time
            delta_seconds = pending_log_alt_time - chosen_time
            log_entry = DecisionLogEntry(
                lap=pending_log_event.lap,
                event_type=pending_log_event.type,
                choice=pending_log_choice,
                delta_seconds=delta_seconds,
            )
            state = dataclasses.replace(state, decision_log=state.decision_log + [log_entry])
            pending_log_event = None
            pending_log_alt_time = None
            pending_log_choice = None

        if state.cars[0].retired_lap is not None:
            # Nothing left for the player to decide - free-run to the finish.
            continue

        if events:
            chosen = _pick_priority_event(events)
            state = dataclasses.replace(state, pending_decision=chosen)
            return state, laps, chosen

    return state, laps, None
