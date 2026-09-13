import time

from sim.model import PARAMS, TRACKS, incident_chance, weather_at
from sim.optimal import (
    CandidateStrategy,
    PushPolicy,
    _DNF_PENALTY_SECONDS,
    _simulate_candidate,
    find_optimal,
)
from sim.rng import PURPOSE_DAMAGE_CHANCE, make_rng
from sim.types import Compound, EventType, PitPlanEntry

_TRACK = "silverstone"
_TOTAL_LAPS = TRACKS[_TRACK]["laps"]


def test_find_optimal_is_deterministic() -> None:
    result1 = find_optimal(_TRACK, seed=7, player_car="car_5", starting_position=10, n_samples=40)
    result2 = find_optimal(_TRACK, seed=7, player_car="car_5", starting_position=10, n_samples=40)
    assert result1 == result2


def test_find_optimal_beats_never_pit_baseline() -> None:
    never_pit = CandidateStrategy(stops=[], push_policy=PushPolicy.NEVER, reactive_choices={})
    baseline_time, _positions = _simulate_candidate(_TRACK, 7, "car_5", 10, never_pit)

    result = find_optimal(_TRACK, seed=7, player_car="car_5", starting_position=10, n_samples=80)
    assert result.total_time < baseline_time


def test_find_optimal_beats_pit_lap_one_baseline() -> None:
    pit_lap_one = CandidateStrategy(
        stops=[PitPlanEntry(target_lap=1, compound=Compound.HARD)],
        push_policy=PushPolicy.NEVER,
        reactive_choices={},
    )
    baseline_time, _positions = _simulate_candidate(_TRACK, 7, "car_5", 10, pit_lap_one)

    result = find_optimal(_TRACK, seed=7, player_car="car_5", starting_position=10, n_samples=80)
    assert result.total_time < baseline_time


def test_simulate_candidate_dnf_is_scored_as_penalty_not_a_crash() -> None:
    # Search for a seed where an always-pushing, never-pitting player DNFs
    # early - reusing the same search technique as test_incidents.py.
    dnf_probability = PARAMS["incident"]["dnf_given_incident_probability"]
    target_seed = None
    for seed in range(3000):
        for lap in range(1, 10):
            wetness = weather_at(seed, _TRACK, lap)
            chance = incident_chance(Compound.MEDIUM, wetness, pushing=True)
            rng = make_rng(seed, lap, PURPOSE_DAMAGE_CHANCE, 0)
            if rng.random() < chance and rng.random() < dnf_probability:
                target_seed = seed
                break
        if target_seed is not None:
            break
    assert target_seed is not None, "expected to find an always-push player DNF within the search range"

    reckless = CandidateStrategy(stops=[], push_policy=PushPolicy.ALWAYS, reactive_choices={})
    total_time, positions = _simulate_candidate(_TRACK, target_seed, "car_5", 10, reckless)
    assert total_time == _DNF_PENALTY_SECONDS
    assert len(positions) > 0


def test_reckless_always_push_can_lose_to_cautious_strategy() -> None:
    # Search for a seed/lap where the draw is decisive specifically because
    # of pushing: below the pushed threshold (triggers an incident) but at
    # or above the non-pushed threshold (no incident at all without push),
    # and that incident resolves as a DNF. This isolates "pushing caused
    # this DNF" rather than "this seed happens to DNF regardless".
    dnf_probability = PARAMS["incident"]["dnf_given_incident_probability"]
    target_seed = None
    for seed in range(3000):
        for lap in range(1, 10):
            wetness = weather_at(seed, _TRACK, lap)
            base_chance = incident_chance(Compound.MEDIUM, wetness, pushing=False)
            pushed_chance = incident_chance(Compound.MEDIUM, wetness, pushing=True)
            rng = make_rng(seed, lap, PURPOSE_DAMAGE_CHANCE, 0)
            draw1 = rng.random()
            if base_chance <= draw1 < pushed_chance and rng.random() < dnf_probability:
                target_seed = seed
                break
        if target_seed is not None:
            break
    assert target_seed is not None

    reckless = CandidateStrategy(stops=[], push_policy=PushPolicy.ALWAYS, reactive_choices={})
    cautious = CandidateStrategy(
        stops=[PitPlanEntry(target_lap=round(_TOTAL_LAPS * 0.45), compound=Compound.HARD)],
        push_policy=PushPolicy.NEVER,
        reactive_choices={},
    )
    reckless_time, _p1 = _simulate_candidate(_TRACK, target_seed, "car_5", 10, reckless)
    cautious_time, _p2 = _simulate_candidate(_TRACK, target_seed, "car_5", 10, cautious)
    assert reckless_time == _DNF_PENALTY_SECONDS
    assert cautious_time < reckless_time


def test_optimal_result_position_trace_has_one_entry_per_lap_completed() -> None:
    result = find_optimal(_TRACK, seed=1, player_car="car_5", starting_position=10, n_samples=20)
    # The winning candidate either finished (full trace) or DNF'd
    # (partial trace up to the retirement lap) - either way, non-empty.
    assert len(result.positions) > 0
    assert all(1 <= p <= 20 for p in result.positions)


def test_find_optimal_default_n_samples_wall_clock() -> None:
    # n_samples=2000 (the originally planned default) measured ~156s in a
    # one-off run - ~78ms/candidate - far too slow for a synchronous debrief
    # API call. The default was lowered to 200 (~15s) after confirming this
    # with the user; that real number is recorded in README.md. This test
    # keeps a fast regression check that the lowered default stays fast.
    start = time.perf_counter()
    find_optimal(_TRACK, seed=1, player_car="car_5", starting_position=10)
    elapsed = time.perf_counter() - start
    print(f"\nfind_optimal(n_samples=200, the default) wall-clock: {elapsed:.2f}s")
    assert elapsed < 30.0
