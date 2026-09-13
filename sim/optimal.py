from dataclasses import dataclass
from enum import Enum

import numpy as np

from sim.model import TRACKS
from sim.race import is_finished, new_race, run_to_next_decision
from sim.rng import PURPOSE_OPTIMAL_SEARCH, make_rng
from sim.types import Compound, Decision, Event, EventType, PitPlanEntry, State

_DNF_PENALTY_SECONDS = 100_000.0

_STOP_COMPOUNDS = [Compound.SOFT, Compound.MEDIUM, Compound.HARD]

_REACTIVE_OPTIONS: dict[EventType, list[str]] = {
    EventType.DAMAGE: ["repair", "stay_out"],
    EventType.SAFETY_CAR: ["pit_soft", "pit_medium", "pit_hard", "hold_position"],
    EventType.RAIN_START: ["stay_out", "pit_inter", "pit_wet"],
    EventType.RAIN_END: ["pit_soft", "pit_medium", "pit_hard", "stay_out"],
}


class PushPolicy(str, Enum):
    NEVER = "never"
    ALWAYS = "always"


@dataclass(frozen=True)
class CandidateStrategy:
    stops: list[PitPlanEntry]
    push_policy: PushPolicy
    reactive_choices: dict[EventType, str]


@dataclass(frozen=True)
class OptimalResult:
    total_time: float
    strategy: CandidateStrategy
    positions: list[int]


def _random_candidate(rng: np.random.Generator, total_laps: int) -> CandidateStrategy:
    num_stops = 1 if rng.random() < 0.5 else 2
    stops: list[PitPlanEntry] = []
    if num_stops == 1:
        target = int(rng.integers(round(total_laps * 0.25), round(total_laps * 0.75)))
        compound = _STOP_COMPOUNDS[int(rng.integers(0, len(_STOP_COMPOUNDS)))]
        stops.append(PitPlanEntry(target_lap=target, compound=compound))
    else:
        first = int(rng.integers(round(total_laps * 0.2), round(total_laps * 0.45)))
        second = int(rng.integers(round(total_laps * 0.55), round(total_laps * 0.85)))
        for target in (first, second):
            compound = _STOP_COMPOUNDS[int(rng.integers(0, len(_STOP_COMPOUNDS)))]
            stops.append(PitPlanEntry(target_lap=target, compound=compound))

    push_policy = PushPolicy.ALWAYS if rng.random() < 0.5 else PushPolicy.NEVER
    reactive_choices = {
        event_type: options[int(rng.integers(0, len(options)))] for event_type, options in _REACTIVE_OPTIONS.items()
    }
    return CandidateStrategy(stops=stops, push_policy=push_policy, reactive_choices=reactive_choices)


def _auto_decision(candidate: CandidateStrategy, event: Event, player_pit_count: int) -> Decision:
    if event.type is EventType.PIT_OPPORTUNITY:
        if player_pit_count < len(candidate.stops):
            compound = candidate.stops[player_pit_count].compound
            return Decision(choice=f"pit_{compound.name.lower()}")
        return Decision(choice="stay_out")
    if event.type is EventType.OVERTAKEN:
        choice = "push" if candidate.push_policy is PushPolicy.ALWAYS else "hold_position"
        return Decision(choice=choice)
    choice = candidate.reactive_choices.get(event.type, event.options[0])
    return Decision(choice=choice)


def _simulate_candidate(
    track: str, seed: int, player_car: str, starting_position: int, candidate: CandidateStrategy
) -> tuple[float, list[int]]:
    state: State = new_race(track, seed, player_car, starting_position)
    positions: list[int] = []
    decision: Decision | None = Decision(push=True) if candidate.push_policy is PushPolicy.ALWAYS else None

    while not is_finished(state):
        state, laps, event = run_to_next_decision(state, decision, seed=seed)
        for lap_trace in laps:
            player_entry = next(c for c in lap_trace.cars if c.id == 0)
            positions.append(player_entry.position)
        decision = None
        if event is not None:
            decision = _auto_decision(candidate, event, state.cars[0].pit_count)

    player = state.cars[0]
    if player.retired_lap is not None:
        return _DNF_PENALTY_SECONDS, positions
    return player.total_time, positions


def find_optimal(
    track: str, seed: int, player_car: str, starting_position: int, n_samples: int = 500
) -> OptimalResult:
    total_laps = TRACKS[track]["laps"]
    best: OptimalResult | None = None
    for i in range(n_samples):
        rng = make_rng(seed, i, PURPOSE_OPTIMAL_SEARCH)
        candidate = _random_candidate(rng, total_laps)
        total_time, positions = _simulate_candidate(track, seed, player_car, starting_position, candidate)
        if best is None or total_time < best.total_time:
            best = OptimalResult(total_time=total_time, strategy=candidate, positions=positions)
    assert best is not None
    return best
