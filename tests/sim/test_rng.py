import numpy as np

from sim.rng import (
    PURPOSE_DAMAGE_CHANCE,
    PURPOSE_NOISE,
    PURPOSE_OPTIMAL_SEARCH,
    PURPOSE_PIT_LOSS,
    PURPOSE_SAFETY_CAR_TRIGGER,
    PURPOSE_WEATHER,
    make_rng,
)


def test_same_inputs_give_identical_draws() -> None:
    rng1 = make_rng(42, 10, PURPOSE_NOISE, 3)
    rng2 = make_rng(42, 10, PURPOSE_NOISE, 3)
    assert rng1.random(20).tolist() == rng2.random(20).tolist()


def test_different_lap_gives_different_draws() -> None:
    rng1 = make_rng(42, 10, PURPOSE_NOISE)
    rng2 = make_rng(42, 11, PURPOSE_NOISE)
    assert rng1.random(10).tolist() != rng2.random(10).tolist()


def test_different_purpose_gives_different_draws() -> None:
    rng1 = make_rng(42, 10, PURPOSE_NOISE)
    rng2 = make_rng(42, 10, PURPOSE_PIT_LOSS)
    assert rng1.random(10).tolist() != rng2.random(10).tolist()


def test_different_car_id_gives_different_draws() -> None:
    rng1 = make_rng(42, 10, PURPOSE_NOISE, 1)
    rng2 = make_rng(42, 10, PURPOSE_NOISE, 2)
    assert rng1.random(10).tolist() != rng2.random(10).tolist()


def test_different_seed_gives_different_draws() -> None:
    rng1 = make_rng(1, 10, PURPOSE_NOISE)
    rng2 = make_rng(2, 10, PURPOSE_NOISE)
    assert rng1.random(10).tolist() != rng2.random(10).tolist()


def test_purpose_constants_are_distinct() -> None:
    purposes = [
        PURPOSE_NOISE,
        PURPOSE_PIT_LOSS,
        PURPOSE_WEATHER,
        PURPOSE_DAMAGE_CHANCE,
        PURPOSE_SAFETY_CAR_TRIGGER,
        PURPOSE_OPTIMAL_SEARCH,
    ]
    assert len(set(purposes)) == len(purposes)


def test_make_rng_returns_a_generator() -> None:
    rng = make_rng(1, 0, PURPOSE_NOISE)
    assert isinstance(rng, np.random.Generator)


def test_streams_are_statistically_decorrelated() -> None:
    # A crude but effective decorrelation check: draws from two nearby
    # streams (adjacent laps) should not be linearly correlated.
    n = 2000
    rng1 = make_rng(42, 1, PURPOSE_NOISE)
    rng2 = make_rng(42, 2, PURPOSE_NOISE)
    a = rng1.random(n)
    b = rng2.random(n)
    correlation = float(np.corrcoef(a, b)[0, 1])
    assert abs(correlation) < 0.1
