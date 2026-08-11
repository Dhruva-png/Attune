from __future__ import annotations

from dataclasses import dataclass

from attune.core.entities.fatigue import FatigueLevel


@dataclass(frozen=True, slots=True)
class Scenario:
    """Parameters driving one synthetic work session.

    Everything here is a *rate* or *range*, not a fixed script — the
    generator samples from these to produce a session that looks like real
    recorded behaviour rather than a repeating pattern.
    """

    name: str
    focus_baseline: float  # 0-100, center of the focus-score random walk
    focus_volatility: float  # per-tick noise amplitude
    focus_trend_per_hour: float  # drift added per hour elapsed (+improving, -declining)
    posture_good_ratio: float  # fraction of the session spent in good posture
    phone_pickups_per_hour: float
    phone_pickup_duration_range_s: tuple[int, int]
    yawns_per_hour: float
    long_blinks_per_hour: float
    face_touches_per_hour: float
    break_count_range: tuple[int, int]
    break_duration_range_s: tuple[int, int]
    fatigue_progression: tuple[FatigueLevel, ...]


GREAT_FOCUS_DAY = Scenario(
    name="great_focus_day",
    focus_baseline=85.0,
    focus_volatility=6.0,
    focus_trend_per_hour=-1.5,
    posture_good_ratio=0.9,
    phone_pickups_per_hour=0.5,
    phone_pickup_duration_range_s=(5, 20),
    yawns_per_hour=0.3,
    long_blinks_per_hour=0.5,
    face_touches_per_hour=0.5,
    break_count_range=(1, 2),
    break_duration_range_s=(180, 420),
    fatigue_progression=(FatigueLevel.FRESH, FatigueLevel.NORMAL),
)

DISTRACTED_DAY = Scenario(
    name="distracted_day",
    focus_baseline=52.0,
    focus_volatility=14.0,
    focus_trend_per_hour=-2.0,
    posture_good_ratio=0.55,
    phone_pickups_per_hour=4.5,
    phone_pickup_duration_range_s=(20, 90),
    yawns_per_hour=1.0,
    long_blinks_per_hour=1.5,
    face_touches_per_hour=2.0,
    break_count_range=(2, 4),
    break_duration_range_s=(120, 600),
    fatigue_progression=(FatigueLevel.NORMAL, FatigueLevel.TIRED),
)

LOW_ENERGY_DAY = Scenario(
    name="low_energy_day",
    focus_baseline=48.0,
    focus_volatility=10.0,
    focus_trend_per_hour=-4.0,
    posture_good_ratio=0.4,
    phone_pickups_per_hour=2.0,
    phone_pickup_duration_range_s=(15, 60),
    yawns_per_hour=3.0,
    long_blinks_per_hour=4.0,
    face_touches_per_hour=3.0,
    break_count_range=(1, 3),
    break_duration_range_s=(180, 900),
    fatigue_progression=(FatigueLevel.NORMAL, FatigueLevel.TIRED, FatigueLevel.VERY_TIRED),
)

AVERAGE_DAY = Scenario(
    name="average_day",
    focus_baseline=68.0,
    focus_volatility=10.0,
    focus_trend_per_hour=-1.0,
    posture_good_ratio=0.7,
    phone_pickups_per_hour=1.5,
    phone_pickup_duration_range_s=(10, 45),
    yawns_per_hour=0.8,
    long_blinks_per_hour=1.0,
    face_touches_per_hour=1.0,
    break_count_range=(1, 3),
    break_duration_range_s=(180, 600),
    fatigue_progression=(FatigueLevel.FRESH, FatigueLevel.NORMAL, FatigueLevel.TIRED),
)

SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in (GREAT_FOCUS_DAY, DISTRACTED_DAY, LOW_ENERGY_DAY, AVERAGE_DAY)
}

# A plausible week: a strong start, a rough Wednesday, tapering into a tired
# Friday, quiet weekend — used by generate_week() unless overridden.
DEFAULT_WEEK_PLAN: tuple[Scenario | None, ...] = (
    GREAT_FOCUS_DAY,  # Monday
    AVERAGE_DAY,  # Tuesday
    DISTRACTED_DAY,  # Wednesday
    AVERAGE_DAY,  # Thursday
    LOW_ENERGY_DAY,  # Friday
    None,  # Saturday - no session
    None,  # Sunday - no session
)

__all__ = [
    "AVERAGE_DAY",
    "DEFAULT_WEEK_PLAN",
    "DISTRACTED_DAY",
    "GREAT_FOCUS_DAY",
    "LOW_ENERGY_DAY",
    "SCENARIOS",
    "Scenario",
]
