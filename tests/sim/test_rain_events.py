from sim.model import PARAMS, TRACKS, weather_at
from sim.race import detect_rain_end, detect_rain_start, is_finished, new_race, step
from sim.types import EventType


def test_detect_rain_start_fires_on_crossing_above_threshold() -> None:
    event = detect_rain_start(prev_wetness=0.05, wetness=0.30, lap=12)
    assert event is not None
    assert event.type is EventType.RAIN_START
    assert event.lap == 12
    assert set(event.options) == {"stay_out", "pit_inter", "pit_wet"}
    assert event.context["wetness"] == 0.30


def test_detect_rain_start_does_not_fire_if_already_wet() -> None:
    assert detect_rain_start(prev_wetness=0.40, wetness=0.45, lap=12) is None


def test_detect_rain_start_does_not_fire_if_staying_dry() -> None:
    assert detect_rain_start(prev_wetness=0.02, wetness=0.05, lap=12) is None


def test_detect_rain_start_does_not_fire_on_exact_threshold_from_above() -> None:
    assert detect_rain_start(prev_wetness=0.20, wetness=0.15, lap=12) is None


def test_detect_rain_end_fires_on_crossing_below_threshold() -> None:
    event = detect_rain_end(prev_wetness=0.30, wetness=0.05, lap=20)
    assert event is not None
    assert event.type is EventType.RAIN_END
    assert event.lap == 20
    assert set(event.options) == {"pit_soft", "pit_medium", "pit_hard", "stay_out"}
    assert event.context["wetness"] == 0.05


def test_detect_rain_end_does_not_fire_if_already_dry() -> None:
    assert detect_rain_end(prev_wetness=0.05, wetness=0.02, lap=20) is None


def test_detect_rain_end_does_not_fire_if_staying_wet() -> None:
    assert detect_rain_end(prev_wetness=0.40, wetness=0.35, lap=20) is None


def _find_rain_start_lap(seed: int, track: str, total_laps: int) -> int | None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    prev = weather_at(seed, track, 0)
    for lap in range(1, total_laps + 1):
        current = weather_at(seed, track, lap)
        if prev < threshold <= current:
            return lap
        prev = current
    return None


def _find_rain_end_lap(seed: int, track: str, total_laps: int, after_lap: int) -> int | None:
    threshold = PARAMS["weather_trajectory"]["rain_threshold"]
    prev = weather_at(seed, track, after_lap)
    for lap in range(after_lap + 1, total_laps + 1):
        current = weather_at(seed, track, lap)
        if prev >= threshold > current:
            return lap
        prev = current
    return None


def test_step_emits_rain_start_event_when_weather_crosses_threshold() -> None:
    track = "silverstone"
    total_laps = TRACKS[track]["laps"]
    target_seed = None
    target_lap = None
    for seed in range(200):
        lap = _find_rain_start_lap(seed, track, total_laps)
        if lap is not None and lap > 1:
            target_seed, target_lap = seed, lap
            break
    assert target_seed is not None and target_lap is not None

    state = new_race(track, seed=target_seed, player_car="car_4", starting_position=10)
    while state.lap < target_lap - 1:
        state, _trace, _events = step(state, None, seed=state.seed)
    state, trace, events = step(state, None, seed=state.seed)

    assert any(e.type is EventType.RAIN_START for e in events)
    assert trace.wetness == weather_at(target_seed, track, target_lap)


def test_step_emits_rain_end_event_when_weather_clears() -> None:
    track = "silverstone"
    total_laps = TRACKS[track]["laps"]
    target_seed = None
    start_lap = None
    end_lap = None
    for seed in range(200):
        lap = _find_rain_start_lap(seed, track, total_laps)
        if lap is None:
            continue
        clear_lap = _find_rain_end_lap(seed, track, total_laps, after_lap=lap)
        if clear_lap is not None:
            target_seed, start_lap, end_lap = seed, lap, clear_lap
            break
    assert target_seed is not None and end_lap is not None

    state = new_race(track, seed=target_seed, player_car="car_4", starting_position=10)
    while state.lap < end_lap - 1:
        state, _trace, _events = step(state, None, seed=state.seed)
    state, _trace, events = step(state, None, seed=state.seed)

    assert any(e.type is EventType.RAIN_END for e in events)


def test_full_race_with_weather_still_completes() -> None:
    track = "silverstone"
    total_laps = TRACKS[track]["laps"]
    state = new_race(track, seed=7, player_car="car_4", starting_position=12)
    while not is_finished(state):
        state, _trace, _events = step(state, None, seed=state.seed)
    assert state.lap == total_laps
