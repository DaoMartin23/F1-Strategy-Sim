from sim.model import PARAMS
from sim.race import detect_overtaken, detect_pitting_opportunity, new_race, step
from sim.types import CarState, Compound, EventType, PitPlanEntry, State


def _car(
    car_id: int,
    car: str = "car_1",
    tyre_age: int = 5,
    total_time: float = 0.0,
    pit_count: int = 0,
    retired_lap: int | None = None,
) -> CarState:
    return CarState(
        id=car_id,
        car=car,
        compound=Compound.MEDIUM,
        tyre_age=tyre_age,
        pit_count=pit_count,
        damage=0,
        total_time=total_time,
        retired_lap=retired_lap,
    )


def _state(cars: list[CarState], **kwargs: object) -> State:
    defaults: dict[str, object] = dict(
        track="silverstone",
        seed=123,
        lap=0,
        push_active=False,
        starting_position=1,
        player_strategy=[],
        pending_decision=None,
        decision_log=[],
        cars=cars,
    )
    defaults.update(kwargs)
    return State(**defaults)  # type: ignore[arg-type]


# --- detect_overtaken ---------------------------------------------------


def test_detect_overtaken_fires_when_rival_total_time_crosses_player() -> None:
    prev_cars = [_car(0, total_time=100.0), _car(1, total_time=105.0)]
    new_cars = [_car(0, total_time=200.0), _car(1, total_time=195.0)]
    event = detect_overtaken(prev_cars, new_cars, player_pitted=False, lap=10)
    assert event is not None
    assert event.type is EventType.OVERTAKEN
    assert set(event.options) == {"push", "hold_position"}
    assert event.context["overtaken_by"] == 1


def test_detect_overtaken_does_not_fire_if_still_ahead() -> None:
    prev_cars = [_car(0, total_time=100.0), _car(1, total_time=105.0)]
    new_cars = [_car(0, total_time=200.0), _car(1, total_time=204.0)]
    assert detect_overtaken(prev_cars, new_cars, player_pitted=False, lap=10) is None


def test_detect_overtaken_does_not_fire_if_player_pitted() -> None:
    prev_cars = [_car(0, total_time=100.0), _car(1, total_time=105.0)]
    new_cars = [_car(0, total_time=230.0), _car(1, total_time=195.0)]
    assert detect_overtaken(prev_cars, new_cars, player_pitted=True, lap=10) is None


def test_detect_overtaken_ignores_retired_rivals() -> None:
    prev_cars = [_car(0, total_time=100.0), _car(1, total_time=105.0)]
    new_cars = [_car(0, total_time=200.0), _car(1, total_time=105.0, retired_lap=9)]
    assert detect_overtaken(prev_cars, new_cars, player_pitted=False, lap=10) is None


def test_detect_overtaken_does_not_fire_if_player_already_retired() -> None:
    prev_cars = [_car(0, total_time=100.0), _car(1, total_time=105.0)]
    new_cars = [_car(0, total_time=100.0, retired_lap=9), _car(1, total_time=95.0)]
    assert detect_overtaken(prev_cars, new_cars, player_pitted=False, lap=10) is None


# --- detect_pitting_opportunity ------------------------------------------


def test_detect_pitting_opportunity_fires_near_target_lap() -> None:
    player = _car(0, tyre_age=5)
    strategy = [PitPlanEntry(target_lap=20, compound=Compound.HARD)]
    event = detect_pitting_opportunity(player, rivals=[], player_strategy=strategy, lap=20)
    assert event is not None
    assert event.type is EventType.PIT_OPPORTUNITY
    assert set(event.options) == {"pit_soft", "pit_medium", "pit_hard", "stay_out"}


def test_detect_pitting_opportunity_does_not_fire_far_from_target() -> None:
    player = _car(0, tyre_age=5)
    strategy = [PitPlanEntry(target_lap=20, compound=Compound.HARD)]
    assert detect_pitting_opportunity(player, rivals=[], player_strategy=strategy, lap=10) is None


def test_detect_pitting_opportunity_does_not_fire_if_already_pitted() -> None:
    player = _car(0, tyre_age=5, pit_count=1)
    strategy = [PitPlanEntry(target_lap=20, compound=Compound.HARD)]
    assert detect_pitting_opportunity(player, rivals=[], player_strategy=strategy, lap=20) is None


def test_detect_pitting_opportunity_fires_past_tyre_cliff() -> None:
    cliff_lap = PARAMS["tyre"][Compound.MEDIUM]["cliff_lap"]
    player = _car(0, tyre_age=cliff_lap + 1)
    event = detect_pitting_opportunity(player, rivals=[], player_strategy=[], lap=40)
    assert event is not None
    assert event.type is EventType.PIT_OPPORTUNITY


def test_detect_pitting_opportunity_context_lists_rivals_pitted() -> None:
    player = _car(0, tyre_age=5)
    strategy = [PitPlanEntry(target_lap=20, compound=Compound.HARD)]
    rivals = [
        _car(1, pit_count=1),
        _car(2, pit_count=0),
        _car(3, pit_count=2, retired_lap=None),
        _car(4, pit_count=1, retired_lap=15),
    ]
    event = detect_pitting_opportunity(player, rivals, strategy, lap=20)
    assert event is not None
    assert set(event.context["rivals_pitted"]) == {1, 3}


# --- step() integration ---------------------------------------------------


def test_step_emits_overtaken_when_faster_rival_passes_player() -> None:
    # car_10 (slowest, +0.7s/lap) vs car_1 (fastest, -0.6s/lap): a ~1.3s/lap
    # gap comfortably dwarfs lap-time noise, so starting them close in total
    # time reliably produces a crossing on the very next lap.
    state = _state(
        [_car(0, car="car_10", total_time=50.0), _car(1, car="car_1", total_time=51.0)],
        starting_position=1,
    )
    _new_state, _trace, events = step(state, None, seed=state.seed)
    assert any(e.type is EventType.OVERTAKEN for e in events)


def test_step_emits_pitting_opportunity_near_player_strategy_target() -> None:
    state = _state(
        [_car(0), _car(1)],
        lap=19,
        player_strategy=[PitPlanEntry(target_lap=20, compound=Compound.HARD)],
    )
    _new_state, _trace, events = step(state, None, seed=state.seed)
    assert any(e.type is EventType.PIT_OPPORTUNITY for e in events)


def test_full_race_with_overtaking_and_pitting_opportunity_still_completes() -> None:
    from sim.race import is_finished

    state = new_race("silverstone", seed=42, player_car="car_4", starting_position=15)
    total_laps = 52
    while not is_finished(state):
        state, _trace, _events = step(state, None, seed=state.seed)
    assert state.lap == total_laps
