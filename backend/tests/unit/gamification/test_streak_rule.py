"""Unit test (T037): streak update rule — timezone-aware day boundary,
consecutive/reset/no-op cases. Pure, no DB needed.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from gamification.domain.streak_rule import update_streak

SAO_PAULO = "America/Sao_Paulo"  # UTC-3, no DST currently observed


class TestUpdateStreak:
    def test_first_ever_activity_starts_streak_at_one(self) -> None:
        result = update_streak(
            streak_current=0,
            streak_last_activity_date=None,
            activity_at=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
            user_timezone=SAO_PAULO,
        )
        assert result.streak_current == 1
        assert result.streak_last_activity_date == date(2026, 1, 10)

    def test_second_activity_same_day_is_a_no_op(self) -> None:
        result = update_streak(
            streak_current=3,
            streak_last_activity_date=date(2026, 1, 10),
            activity_at=datetime(2026, 1, 10, 23, 0, tzinfo=UTC),
            user_timezone=SAO_PAULO,
        )
        assert result.streak_current == 3
        assert result.streak_last_activity_date == date(2026, 1, 10)

    def test_activity_on_consecutive_day_increments_streak(self) -> None:
        result = update_streak(
            streak_current=3,
            streak_last_activity_date=date(2026, 1, 10),
            activity_at=datetime(2026, 1, 11, 12, 0, tzinfo=UTC),
            user_timezone=SAO_PAULO,
        )
        assert result.streak_current == 4
        assert result.streak_last_activity_date == date(2026, 1, 11)

    def test_missed_day_resets_streak_to_one_no_tolerance(self) -> None:
        result = update_streak(
            streak_current=10,
            streak_last_activity_date=date(2026, 1, 1),
            activity_at=datetime(2026, 1, 10, 12, 0, tzinfo=UTC),
            user_timezone=SAO_PAULO,
        )
        assert result.streak_current == 1
        assert result.streak_last_activity_date == date(2026, 1, 10)

    def test_day_boundary_respects_user_timezone_not_utc(self) -> None:
        # 2026-01-11 01:30 UTC is still 2026-01-10 22:30 in America/Sao_Paulo
        # (UTC-3) — should count as the SAME local day as a prior activity
        # on 2026-01-10, not a new day.
        result = update_streak(
            streak_current=2,
            streak_last_activity_date=date(2026, 1, 10),
            activity_at=datetime(2026, 1, 11, 1, 30, tzinfo=UTC),
            user_timezone=SAO_PAULO,
        )
        assert result.streak_current == 2
        assert result.streak_last_activity_date == date(2026, 1, 10)
