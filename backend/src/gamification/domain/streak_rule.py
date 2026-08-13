"""Gamification domain rule (T048): daily streak update, timezone-aware,
no-tolerance reset — data-model.md's GamificationProfile state transitions.

- No prior activity (`streak_last_activity_date is None`): today starts a
  streak of 1.
- Prior activity was already today (in the user's timezone): no-op, same
  count (guards against multiple qualifying activities in one day inflating
  the streak).
- Prior activity was yesterday: consecutive day, `streak_current += 1`.
- Prior activity was any earlier day: the streak is broken — resets to 1
  (today's activity starts a new streak). No partial credit/grace period
  (Clarifications: no tolerance/freeze).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class StreakUpdateResult:
    streak_current: int
    streak_last_activity_date: date


def update_streak(
    *,
    streak_current: int,
    streak_last_activity_date: date | None,
    activity_at: datetime,
    user_timezone: str,
) -> StreakUpdateResult:
    """`activity_at` is converted into `user_timezone` before comparing
    calendar dates, so the day boundary matches the student's local day,
    not UTC or server time."""
    today = activity_at.astimezone(ZoneInfo(user_timezone)).date()

    if streak_last_activity_date is None:
        return StreakUpdateResult(streak_current=1, streak_last_activity_date=today)

    if streak_last_activity_date == today:
        return StreakUpdateResult(streak_current=streak_current, streak_last_activity_date=today)

    if (today - streak_last_activity_date).days == 1:
        return StreakUpdateResult(
            streak_current=streak_current + 1, streak_last_activity_date=today
        )

    return StreakUpdateResult(streak_current=1, streak_last_activity_date=today)
