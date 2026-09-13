from sim.model import PARAMS, weather_at


def test_weather_at_deterministic_for_same_inputs() -> None:
    a = weather_at(seed=5, track="silverstone", lap=20)
    b = weather_at(seed=5, track="silverstone", lap=20)
    assert a == b


def test_weather_at_bounded_between_zero_and_one() -> None:
    for seed in range(50):
        for lap in range(0, 53, 5):
            wetness = weather_at(seed=seed, track="silverstone", lap=lap)
            assert 0.0 <= wetness <= 1.0


def test_weather_at_lap_zero_starts_dry() -> None:
    for seed in range(20):
        wetness = weather_at(seed=seed, track="silverstone", lap=0)
        assert wetness == 0.0


def test_weather_at_rain_can_occur_over_many_seeds() -> None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    found_rain = False
    for seed in range(200):
        for lap in range(1, 53):
            if weather_at(seed=seed, track="silverstone", lap=lap) >= threshold:
                found_rain = True
                break
        if found_rain:
            break
    assert found_rain


def test_weather_at_rain_can_clear_after_starting() -> None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    found_clearing = False
    for seed in range(300):
        was_wet = False
        for lap in range(1, 53):
            wetness = weather_at(seed=seed, track="silverstone", lap=lap)
            if was_wet and wetness < threshold:
                found_clearing = True
                break
            if wetness >= threshold:
                was_wet = True
        if found_clearing:
            break
    assert found_clearing
