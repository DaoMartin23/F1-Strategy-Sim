import numpy as np

PURPOSE_NOISE = 1
PURPOSE_PIT_LOSS = 2
PURPOSE_WEATHER = 3
PURPOSE_DAMAGE_CHANCE = 4
PURPOSE_SAFETY_CAR_TRIGGER = 5
PURPOSE_OPTIMAL_SEARCH = 6
PURPOSE_GRID = 7


def make_rng(seed: int, lap: int, purpose: int, *extra: int) -> np.random.Generator:
    seed_sequence = np.random.SeedSequence([seed, lap, purpose, *extra])
    return np.random.Generator(np.random.PCG64(seed_sequence))
