from __future__ import annotations

from attune.demo.scenarios import DEFAULT_WEEK_PLAN, SCENARIOS, Scenario


def test_all_registered_scenarios_are_internally_consistent() -> None:
    for scenario in SCENARIOS.values():
        assert isinstance(scenario, Scenario)
        assert 0.0 <= scenario.posture_good_ratio <= 1.0
        pickup_range = scenario.phone_pickup_duration_range_s
        assert pickup_range[0] <= pickup_range[1]
        assert scenario.break_count_range[0] <= scenario.break_count_range[1]
        assert scenario.break_duration_range_s[0] <= scenario.break_duration_range_s[1]
        assert len(scenario.fatigue_progression) >= 1


def test_scenario_registry_keyed_by_name() -> None:
    for name, scenario in SCENARIOS.items():
        assert scenario.name == name


def test_default_week_plan_has_seven_days() -> None:
    assert len(DEFAULT_WEEK_PLAN) == 7


def test_default_week_plan_includes_rest_days() -> None:
    assert any(day is None for day in DEFAULT_WEEK_PLAN)
