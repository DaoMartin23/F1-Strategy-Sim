from typing import TypedDict

import numpy as np

from sim.types import Compound


class TyreParams(TypedDict):
    deg_per_lap: float
    cliff_lap: int
    cliff_deg_per_lap: float


class WeatherParams(TypedDict):
    optimal_wetness: float
    penalty_coeff: float


class PitLossParams(TypedDict):
    min: float
    max: float
    typical_mean: float
    typical_std: float
    typical_probability: float


class TrackParams(TypedDict):
    laps: int
    lap_km: float
    base_lap_time: float


class ModelParams(TypedDict):
    fuel_effect_total_seconds: float
    noise_std: float
    push_time_gain: float
    push_extra_wear: int
    damage_penalty_per_level: float
    pit_loss: PitLossParams
    tyre: dict[Compound, TyreParams]
    weather: dict[Compound, WeatherParams]


PARAMS: ModelParams = {
    "fuel_effect_total_seconds": 1.8,
    "noise_std": 0.15,
    "push_time_gain": 0.5,
    "push_extra_wear": 1,
    "damage_penalty_per_level": 0.4,
    "pit_loss": {
        "min": 18.0,
        "max": 30.0,
        "typical_mean": 21.0,
        "typical_std": 0.8,
        "typical_probability": 0.85,
    },
    "tyre": {
        Compound.SOFT: {"deg_per_lap": 0.09, "cliff_lap": 16, "cliff_deg_per_lap": 0.40},
        Compound.MEDIUM: {"deg_per_lap": 0.05, "cliff_lap": 27, "cliff_deg_per_lap": 0.25},
        Compound.HARD: {"deg_per_lap": 0.03, "cliff_lap": 40, "cliff_deg_per_lap": 0.15},
        Compound.INTER: {"deg_per_lap": 0.06, "cliff_lap": 22, "cliff_deg_per_lap": 0.20},
        Compound.WET: {"deg_per_lap": 0.04, "cliff_lap": 30, "cliff_deg_per_lap": 0.15},
    },
    "weather": {
        Compound.SOFT: {"optimal_wetness": 0.0, "penalty_coeff": 26.0},
        Compound.MEDIUM: {"optimal_wetness": 0.0, "penalty_coeff": 24.0},
        Compound.HARD: {"optimal_wetness": 0.0, "penalty_coeff": 22.0},
        Compound.INTER: {"optimal_wetness": 0.35, "penalty_coeff": 12.0},
        Compound.WET: {"optimal_wetness": 0.85, "penalty_coeff": 15.0},
    },
}

CAR_CHOICES: dict[str, float] = {
    "car_1": -0.6,
    "car_2": -0.4,
    "car_3": -0.25,
    "car_4": -0.1,
    "car_5": 0.0,
    "car_6": 0.1,
    "car_7": 0.25,
    "car_8": 0.4,
    "car_9": 0.55,
    "car_10": 0.7,
}

TRACKS: dict[str, TrackParams] = {
    "silverstone": {"laps": 52, "lap_km": 5.891, "base_lap_time": 91.5},
}


def fuel_effect(lap: int, total_laps: int) -> float:
    remaining_fraction = (total_laps - 1 - lap) / (total_laps - 1)
    return PARAMS["fuel_effect_total_seconds"] * remaining_fraction


def tyre_deg(compound: Compound, age: int) -> float:
    params = PARAMS["tyre"][compound]
    linear = params["deg_per_lap"] * age
    over_cliff = max(0, age - params["cliff_lap"])
    cliff = params["cliff_deg_per_lap"] * over_cliff
    return linear + cliff


def weather_penalty(compound: Compound, wetness: float) -> float:
    params = PARAMS["weather"][compound]
    return params["penalty_coeff"] * abs(wetness - params["optimal_wetness"])


def noise(rng: np.random.Generator) -> float:
    return float(rng.normal(0.0, PARAMS["noise_std"]))


def pit_loss(rng: np.random.Generator) -> float:
    params = PARAMS["pit_loss"]
    if rng.random() < params["typical_probability"]:
        value = float(rng.normal(params["typical_mean"], params["typical_std"]))
        return float(np.clip(value, params["min"], params["max"]))
    return float(rng.uniform(params["min"], params["max"]))


def lap_time(
    car: str,
    track: str,
    lap: int,
    compound: Compound,
    tyre_age: int,
    wetness: float,
    rng: np.random.Generator,
    damage: int = 0,
) -> float:
    track_params = TRACKS[track]
    base = track_params["base_lap_time"] + CAR_CHOICES[car]
    return (
        base
        + fuel_effect(lap, track_params["laps"])
        + tyre_deg(compound, tyre_age)
        + weather_penalty(compound, wetness)
        + noise(rng)
        + PARAMS["damage_penalty_per_level"] * damage
    )
