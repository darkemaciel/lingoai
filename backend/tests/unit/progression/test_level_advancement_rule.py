"""Unit test (T035): windowed-accuracy level-advancement rule — advances at
>= 80% over the last 10 (min 5) scored activities, never regresses, a
single miss inside an otherwise-strong window doesn't reset progress.
Pure, no DB/agent needed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from progression.domain.level_advancement_rule import (
    ACCURACY_WINDOW_MAX_SIZE,
    AccuracyWindowEntry,
    apply_scored_activity,
    next_level,
)
from shared_kernel.domain.enums import CEFRLevel

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _window(*correct_flags: bool) -> tuple[AccuracyWindowEntry, ...]:
    return tuple(AccuracyWindowEntry(correct=flag, at=NOW) for flag in correct_flags)


class TestNextLevel:
    def test_advances_through_the_ladder(self) -> None:
        assert next_level(CEFRLevel.A1) is CEFRLevel.A2
        assert next_level(CEFRLevel.B1) is CEFRLevel.B2
        assert next_level(CEFRLevel.C1) is CEFRLevel.C2

    def test_c2_has_no_next_level(self) -> None:
        assert next_level(CEFRLevel.C2) is None


class TestApplyScoredActivity:
    def test_fewer_than_five_activities_never_advances_even_at_100_percent(self) -> None:
        window = _window(True, True, True)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.A1,
            mastery_score=100,
            accuracy_window=window,
            correct=True,
            at=NOW,
        )
        assert result.level_advanced is False
        assert result.cefr_level is CEFRLevel.A1
        assert len(result.accuracy_window) == 4

    def test_advances_at_exactly_five_activities_and_80_percent(self) -> None:
        # 4 correct already recorded; this 5th correct answer makes 5/5 = 100% >= 80%.
        window = _window(True, True, True, True)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.A1,
            mastery_score=80,
            accuracy_window=window,
            correct=True,
            at=NOW,
        )
        assert result.level_advanced is True
        assert result.cefr_level is CEFRLevel.A2
        assert result.mastery_score == 0
        assert result.accuracy_window == ()

    def test_below_threshold_does_not_advance_and_does_not_regress(self) -> None:
        # 3 correct out of 5 recorded = 60%; this 6th wrong answer brings it
        # to 3/6 = 50%, still below 80%.
        window = _window(True, True, True, False, False)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.B1,
            mastery_score=60,
            accuracy_window=window,
            correct=False,
            at=NOW,
        )
        assert result.level_advanced is False
        assert result.cefr_level is CEFRLevel.B1  # explicitly: no regression
        assert result.mastery_score == 50

    def test_single_miss_inside_strong_window_does_not_block_advancement(self) -> None:
        # 8 correct, 1 wrong recorded (9 entries, 88.9%); the 10th (correct)
        # keeps accuracy well above 80% despite the earlier miss.
        window = _window(True, True, True, True, False, True, True, True, True)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.A2,
            mastery_score=88,
            accuracy_window=window,
            correct=True,
            at=NOW,
        )
        assert result.level_advanced is True
        assert result.cefr_level is CEFRLevel.B1

    def test_window_never_exceeds_max_size(self) -> None:
        # C2 is the ceiling — no advancement (and therefore no window
        # clear) is possible here, isolating the trim-to-max-size behavior.
        window = _window(*([True] * ACCURACY_WINDOW_MAX_SIZE))
        result = apply_scored_activity(
            cefr_level=CEFRLevel.C2,
            mastery_score=100,
            accuracy_window=window,
            correct=False,
            at=NOW,
        )
        assert len(result.accuracy_window) == ACCURACY_WINDOW_MAX_SIZE
        # Oldest True entry was dropped in favor of the new False one.
        assert result.accuracy_window[-1].correct is False

    def test_mastery_score_recomputed_from_updated_window(self) -> None:
        window = _window(True, False)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.A1,
            mastery_score=50,
            accuracy_window=window,
            correct=True,
            at=NOW,
        )
        # 2 correct out of 3 = 66.67% -> rounds to 67.
        assert result.mastery_score == 67

    def test_already_at_ceiling_never_advances_past_c2(self) -> None:
        window = _window(True, True, True, True)
        result = apply_scored_activity(
            cefr_level=CEFRLevel.C2,
            mastery_score=80,
            accuracy_window=window,
            correct=True,
            at=NOW,
        )
        assert result.level_advanced is False
        assert result.cefr_level is CEFRLevel.C2
