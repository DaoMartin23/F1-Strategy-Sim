import numpy as np
import pytest

from sim.model import (
    CAR_CHOICES,
    PARAMS,
    TRACKS,
    fuel_effect,
    incident_chance,
    lap_time,
    noise,
    pit_loss,
    safety_car_chance,
    tyre_deg,
    weather_penalty,
)
from sim.types import Compound


def test_fuel_effect_decreases_over_race() -> None:
    total_laps = TRACKS["silverstone"]["laps"]
    early = fuel_effect(0, total_laps)
    late = fuel_effect(total_laps - 1, total_laps)
    assert early > late
    assert late == pytest.approx(0.0, abs=0.05)


def test_fuel_effect_never_negative() -> None:
    total_laps = TRACKS["silverstone"]["laps"]
    for lap in range(total_laps):
        assert fuel_effect(lap, total_laps) >= 0.0


def test_tyre_deg_increases_with_age_before_cliff() -> None:
    for compound in Compound:
        cliff_lap = PARAMS["tyre"][compound]["cliff_lap"]
        early_age = max(1, cliff_lap - 5)
        later_age = cliff_lap - 1
        assert tyre_deg(compound, early_age) < tyre_deg(compound, later_age)


def test_tyre_deg_cliff_accelerates_wear() -> None:
    for compound in Compound:
        cliff_lap = PARAMS["tyre"][compound]["cliff_lap"]
        step_before = tyre_deg(compound, cliff_lap) - tyre_deg(compound, cliff_lap - 1)
        step_after = tyre_deg(compound, cliff_lap + 2) - tyre_deg(compound, cliff_lap + 1)
        assert step_after > step_before


def test_weather_penalty_slicks_worse_in_rain() -> None:
    for compound in (Compound.SOFT, Compound.MEDIUM, Compound.HARD):
        assert weather_penalty(compound, 0.0) == pytest.approx(0.0, abs=0.01)
        assert weather_penalty(compound, 1.0) > 15.0


def test_weather_penalty_inter_and_wet_penalized_off_optimal() -> None:
    for compound in (Compound.INTER, Compound.WET):
        optimal = PARAMS["weather"][compound]["optimal_wetness"]
        assert weather_penalty(compound, optimal) == pytest.approx(0.0, abs=0.01)
        assert weather_penalty(compound, 0.0) > 0.0


def test_noise_is_small_and_roughly_zero_mean() -> None:
    rng = np.random.default_rng(1)
    draws = [noise(rng) for _ in range(5000)]
    assert abs(float(np.mean(draws))) < 0.05
    assert max(abs(d) for d in draws) < 1.0


def test_pit_loss_within_bounds_and_centred() -> None:
    rng = np.random.default_rng(2)
    draws = [pit_loss(rng) for _ in range(5000)]
    assert all(18.0 <= d <= 30.0 for d in draws)
    in_band = sum(1 for d in draws if 20.0 <= d <= 22.0)
    assert in_band / len(draws) > 0.5


def test_car_choices_differ_in_base_time() -> None:
    offsets = set(CAR_CHOICES.values())
    assert len(offsets) > 1


def test_lap_time_deterministic_given_rng_state() -> None:
    rng1 = np.random.default_rng(7)
    rng2 = np.random.default_rng(7)
    car = next(iter(CAR_CHOICES))
    t1 = lap_time(car, "silverstone", 10, Compound.MEDIUM, 5, 0.0, rng1)
    t2 = lap_time(car, "silverstone", 10, Compound.MEDIUM, 5, 0.0, rng2)
    assert t1 == t2


def test_lap_time_damage_penalty() -> None:
    car = next(iter(CAR_CHOICES))
    rng_undamaged = np.random.default_rng(11)
    rng_damaged = np.random.default_rng(11)
    undamaged = lap_time(car, "silverstone", 10, Compound.MEDIUM, 5, 0.0, rng_undamaged, damage=0)
    damaged = lap_time(car, "silverstone", 10, Compound.MEDIUM, 5, 0.0, rng_damaged, damage=2)
    expected_penalty = 2 * PARAMS["damage_penalty_per_level"]
    assert damaged - undamaged == pytest.approx(expected_penalty)


def test_incident_chance_matches_baseline_when_neutral() -> None:
    chance = incident_chance(Compound.SOFT, wetness=0.0, pushing=False)
    assert chance == pytest.approx(PARAMS["incident"]["base_chance_per_lap"])


def test_incident_chance_increases_with_weather_mismatch() -> None:
    neutral = incident_chance(Compound.SOFT, wetness=0.0, pushing=False)
    mismatched = incident_chance(Compound.SOFT, wetness=1.0, pushing=False)
    assert mismatched > neutral


def test_incident_chance_increases_when_pushing() -> None:
    not_pushing = incident_chance(Compound.MEDIUM, wetness=0.0, pushing=False)
    pushing = incident_chance(Compound.MEDIUM, wetness=0.0, pushing=True)
    assert pushing > not_pushing
    assert pushing - not_pushing == pytest.approx(PARAMS["incident"]["push_bonus"])


def test_safety_car_chance_matches_base_when_no_incident() -> None:
    assert safety_car_chance(incident_occurred=False) == pytest.approx(PARAMS["safety_car"]["base_chance_per_lap"])


def test_safety_car_chance_boosted_by_incident() -> None:
    without = safety_car_chance(incident_occurred=False)
    with_incident = safety_car_chance(incident_occurred=True)
    assert with_incident > without
    assert with_incident - without == pytest.approx(PARAMS["safety_car"]["incident_bonus"])


def test_lap_time_faster_with_less_fuel() -> None:
    car = next(iter(CAR_CHOICES))
    rng_a = np.random.default_rng(9)
    rng_b = np.random.default_rng(9)
    early = lap_time(car, "silverstone", 1, Compound.MEDIUM, 1, 0.0, rng_a)
    late = lap_time(car, "silverstone", 45, Compound.MEDIUM, 1, 0.0, rng_b)
    assert late < early
