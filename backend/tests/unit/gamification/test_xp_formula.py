"""Unit test (T036): XP formula, research.md §7 —
`base_xp(type) * max(0.25, performance_score)`, rounded. Pure, no DB needed.
"""

from __future__ import annotations

import pytest

from gamification.domain.xp_rule import BASE_XP_BY_ACTIVITY_TYPE, calculate_xp
from shared_kernel.domain.enums import ActivityType


class TestCalculateXp:
    def test_full_score_awards_full_base_xp(self) -> None:
        assert calculate_xp(ActivityType.WRITING_EXERCISE, 1.0) == 10

    def test_zero_score_still_awards_floor_rate_xp(self) -> None:
        # 0.25 floor, never zero — FR-9's "reinforce, never punish".
        assert calculate_xp(ActivityType.WRITING_EXERCISE, 0.0) == round(10 * 0.25)

    def test_score_below_floor_is_clamped_to_floor(self) -> None:
        assert calculate_xp(ActivityType.LISTENING_EXERCISE, 0.1) == calculate_xp(
            ActivityType.LISTENING_EXERCISE, 0.25
        )

    def test_score_above_floor_uses_actual_score(self) -> None:
        assert calculate_xp(ActivityType.SPEAKING_EXERCISE, 0.5) == round(10 * 0.5)

    @pytest.mark.parametrize(
        ("activity_type", "expected_base"),
        [
            (ActivityType.CONVERSATION_PROMPT, 5),
            (ActivityType.WRITING_EXERCISE, 10),
            (ActivityType.SPEAKING_EXERCISE, 10),
            (ActivityType.LISTENING_EXERCISE, 8),
        ],
    )
    def test_base_xp_table_matches_research_md(
        self, activity_type: ActivityType, expected_base: int
    ) -> None:
        assert BASE_XP_BY_ACTIVITY_TYPE[activity_type] == expected_base
        assert calculate_xp(activity_type, 1.0) == expected_base

    def test_result_is_rounded_to_nearest_integer(self) -> None:
        # base_xp=5 (conversation), score=0.6 -> 3.0 exactly, still an int.
        result = calculate_xp(ActivityType.CONVERSATION_PROMPT, 0.6)
        assert isinstance(result, int)
        assert result == 3
