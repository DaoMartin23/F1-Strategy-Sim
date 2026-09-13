import dataclasses

import pytest

from sim.model import CAR_CHOICES, TRACKS
from sim.race import (
    RivalTemplate,
    _compute_grid,
    _rival_car_choice,
    _rival_template,
    is_finished,
    new_race,
    rival_plan,
    step,
)
from sim.types import Compound


def test_new_race_creates_twenty_cars() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    assert len(state.cars) == 20
    assert {car.id for car in state.cars} == set(range(20))


def test_new_race_player_is_car_zero_with_chosen_car() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    assert state.cars[0].id == 0
    assert state.cars[0].car == "car_5"


def test_new_race_sets_starting_position() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=7)
    assert state.starting_position == 7


def test_new_race_all_cars_start_fresh() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    for car in state.cars:
        assert car.total_time == 0.0
        assert car.tyre_age == 0
        assert car.pit_count == 0
        assert car.damage == 0
        assert car.retired_lap is None
        assert car.compound == Compound.MEDIUM


def test_new_race_is_deterministic_for_same_inputs() -> None:
    state1 = new_race("silverstone", seed=42, player_car="car_3", starting_position=5)
    state2 = new_race("silverstone", seed=42, player_car="car_3", starting_position=5)
    assert state1 == state2


def test_new_race_rival_cars_independent_of_seed() -> None:
    state1 = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    state2 = new_race("silverstone", seed=999, player_car="car_5", starting_position=10)
    rival_cars_1 = [car.car for car in state1.cars if car.id != 0]
    rival_cars_2 = [car.car for car in state2.cars if car.id != 0]
    assert rival_cars_1 == rival_cars_2


def test_rival_car_choice_is_deterministic_and_covers_table() -> None:
    choices = {_rival_car_choice(car_id) for car_id in range(1, 20)}
    assert choices.issubset(set(CAR_CHOICES.keys()))
    assert len(choices) > 1


def test_compute_grid_places_player_at_starting_position() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=8)
    grid = _compute_grid(state.starting_position, state.cars, seed=1)
    assert grid[0] == 8
    assert set(grid.values()) == set(range(1, 21))


def test_compute_grid_is_deterministic_for_same_seed() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    grid1 = _compute_grid(state.starting_position, state.cars, seed=123)
    grid2 = _compute_grid(state.starting_position, state.cars, seed=123)
    assert grid1 == grid2


def test_compute_grid_faster_cars_more_likely_but_not_guaranteed_higher() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=20)
    rivals = [car for car in state.cars if car.id != 0]
    fastest = min(rivals, key=lambda c: CAR_CHOICES[c.car])
    slowest = max(rivals, key=lambda c: CAR_CHOICES[c.car])
    assert CAR_CHOICES[fastest.car] < CAR_CHOICES[slowest.car]

    n = 300
    fastest_slots = []
    slowest_slots = []
    slowest_ever_ahead = False
    for seed in range(n):
        grid = _compute_grid(state.starting_position, state.cars, seed=seed)
        fastest_slots.append(grid[fastest.id])
        slowest_slots.append(grid[slowest.id])
        if grid[slowest.id] < grid[fastest.id]:
            slowest_ever_ahead = True

    # More likely to start ahead, on average...
    assert sum(fastest_slots) / n < sum(slowest_slots) / n
    # ...but never guaranteed - genuine randomness, not a strict pace sort.
    assert slowest_ever_ahead


def test_rival_template_assignment_is_deterministic() -> None:
    assert _rival_template(pace_offset=-0.5, grid_slot=5) == RivalTemplate.TWO_STOP
    assert _rival_template(pace_offset=0.5, grid_slot=5) == RivalTemplate.ONE_STOP
    assert _rival_template(pace_offset=0.5, grid_slot=18) == RivalTemplate.TWO_STOP


def test_rival_plan_one_stop_has_single_entry() -> None:
    plan = rival_plan(car_id=7, template=RivalTemplate.ONE_STOP, total_laps=52)
    assert len(plan) == 1
    assert 0 < plan[0].target_lap < 52


def test_rival_plan_two_stop_has_two_ordered_entries() -> None:
    plan = rival_plan(car_id=7, template=RivalTemplate.TWO_STOP, total_laps=52)
    assert len(plan) == 2
    assert plan[0].target_lap < plan[1].target_lap


def test_full_race_same_seed_and_choices_is_bit_identical() -> None:
    def run() -> object:
        state = new_race("silverstone", seed=55, player_car="car_4", starting_position=12)
        while not is_finished(state):
            state, _trace, _events = step(state, None, seed=state.seed)
        return state

    assert run() == run()


def test_rivals_all_pit_at_least_once_over_a_full_race() -> None:
    state = new_race("silverstone", seed=7, player_car="car_4", starting_position=12)
    while not is_finished(state):
        state, _trace, _events = step(state, None, seed=state.seed)
    for car in state.cars:
        if car.id != 0:
            assert car.pit_count >= 1


def test_rival_pits_on_its_planned_lap() -> None:
    state = new_race("silverstone", seed=7, player_car="car_4", starting_position=12)
    rival = next(car for car in state.cars if car.id != 0)
    grid = _compute_grid(state.starting_position, state.cars, seed=state.seed)
    pace_offset = CAR_CHOICES[rival.car]
    template = _rival_template(pace_offset, grid[rival.id])
    total_laps = TRACKS["silverstone"]["laps"]
    plan = rival_plan(rival.id, template, total_laps)
    target_lap = plan[0].target_lap

    while state.lap < target_lap:
        state, _trace, _events = step(state, None, seed=state.seed)

    updated_rival = next(car for car in state.cars if car.id == rival.id)
    assert updated_rival.tyre_age == 1
    assert updated_rival.pit_count == 1
    assert updated_rival.compound == plan[0].compound


def test_new_race_assigns_a_default_player_strategy() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    assert len(state.player_strategy) >= 1
    for entry in state.player_strategy:
        assert 0 < entry.target_lap < TRACKS["silverstone"]["laps"]


def test_new_race_state_is_frozen_dataclass() -> None:
    state = new_race("silverstone", seed=1, player_car="car_5", starting_position=10)
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.lap = 5  # type: ignore[misc]
