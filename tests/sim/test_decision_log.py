from sim.race import _alternative_choice, is_finished, new_race, run_to_next_decision, step
from sim.types import Decision, Event, EventType

_TRACK = "silverstone"


def _auto_decision(event: Event | None) -> Decision | None:
    if event is None:
        return None
    return Decision(choice=event.options[0])


# --- _alternative_choice ----------------------------------------------


def test_alternative_choice_damage() -> None:
    event = Event(type=EventType.DAMAGE, lap=5, options=["repair", "stay_out"], context={})
    assert _alternative_choice(event, "repair") == "stay_out"
    assert _alternative_choice(event, "stay_out") == "repair"


def test_alternative_choice_overtaken() -> None:
    event = Event(type=EventType.OVERTAKEN, lap=5, options=["push", "hold_position"], context={})
    assert _alternative_choice(event, "push") == "hold_position"
    assert _alternative_choice(event, "hold_position") == "push"


def test_alternative_choice_pitting_opportunity() -> None:
    event = Event(
        type=EventType.PIT_OPPORTUNITY,
        lap=5,
        options=["pit_soft", "pit_medium", "pit_hard", "stay_out"],
        context={},
    )
    assert _alternative_choice(event, "pit_medium") == "stay_out"
    assert _alternative_choice(event, "stay_out") == "pit_soft"


def test_alternative_choice_safety_car() -> None:
    event = Event(
        type=EventType.SAFETY_CAR,
        lap=5,
        options=["pit_soft", "pit_medium", "pit_hard", "hold_position"],
        context={},
    )
    assert _alternative_choice(event, "pit_hard") == "hold_position"
    assert _alternative_choice(event, "hold_position") == "pit_soft"


# --- decision_log / delta_seconds --------------------------------------


def _find_seed_with_two_events() -> tuple[int, list[Event]]:
    for seed in range(200):
        state = new_race(_TRACK, seed=seed, player_car="car_4", starting_position=12)
        decision = None
        found_events: list[Event] = []
        while not is_finished(state) and len(found_events) < 2:
            state, _laps, event = run_to_next_decision(state, decision, seed=state.seed)
            if event is None:
                break
            found_events.append(event)
            decision = _auto_decision(event)
        if len(found_events) >= 2:
            return seed, found_events
    raise AssertionError("expected to find a seed producing at least two events")


def test_run_to_next_decision_adds_no_log_entry_without_a_pending_decision() -> None:
    state = new_race(_TRACK, seed=1, player_car="car_5", starting_position=10)
    assert state.pending_decision is None
    new_state, _laps, _event = run_to_next_decision(state, None, seed=state.seed)
    assert new_state.decision_log == state.decision_log


def test_run_to_next_decision_logs_the_resolved_decision() -> None:
    state = new_race(_TRACK, seed=42, player_car="car_4", starting_position=12)
    state, _laps, event = run_to_next_decision(state, None, seed=state.seed)
    assert event is not None, "expected at least one event for this seed"

    decision = _auto_decision(event)
    resumed_state, _more_laps, _next_event = run_to_next_decision(state, decision, seed=state.seed)

    assert len(resumed_state.decision_log) == 1
    entry = resumed_state.decision_log[0]
    assert entry.lap == event.lap
    assert entry.event_type == event.type
    assert entry.choice == decision.choice  # type: ignore[union-attr]


def test_decision_log_delta_matches_manual_recomputation() -> None:
    state = new_race(_TRACK, seed=42, player_car="car_4", starting_position=12)
    state, _laps, event = run_to_next_decision(state, None, seed=state.seed)
    assert event is not None

    decision = _auto_decision(event)
    assert decision is not None and decision.choice is not None
    alternative = _alternative_choice(event, decision.choice)

    chosen_state, _t1, _e1 = step(state, decision, seed=state.seed)
    alt_state, _t2, _e2 = step(state, Decision(choice=alternative), seed=state.seed)
    expected_delta = alt_state.cars[0].total_time - chosen_state.cars[0].total_time

    resumed_state, _more_laps, _next_event = run_to_next_decision(state, decision, seed=state.seed)
    logged_delta = resumed_state.decision_log[0].delta_seconds
    assert logged_delta == expected_delta


def test_decision_log_accumulates_across_multiple_resolved_events() -> None:
    # Each run_to_next_decision() call resolves the *previous* pending
    # decision (if any) and finds the *next* one - so logging len(events)
    # entries takes one extra call beyond len(events) to resolve the last
    # one found.
    seed, events = _find_seed_with_two_events()
    state = new_race(_TRACK, seed=seed, player_car="car_4", starting_position=12)
    decision = None
    for _ in range(len(events) + 1):
        if is_finished(state):
            break
        state, _laps, event = run_to_next_decision(state, decision, seed=state.seed)
        decision = _auto_decision(event)

    assert len(state.decision_log) == len(events)
    for logged, original_event in zip(state.decision_log, events):
        assert logged.lap == original_event.lap
        assert logged.event_type == original_event.type
