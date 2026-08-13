"""Progression domain rule (T046): windowed-accuracy level advancement.

Per research.md §6 and data-model.md's LearnerSkillProfile state
transitions — pure Python, no DB/agent dependency, unit-tested in isolation
(NFR-7, Constitution §1/§5: the LLM only ever emits a performance signal;
this deterministic rule is what actually decides level advancement).

Rule: a skill's CEFR level advances one step when the accuracy_window (the
last ACCURACY_WINDOW_MAX_SIZE scored activities) has at least
MIN_ACTIVITIES_BEFORE_ADVANCE entries and accuracy >=
ADVANCEMENT_ACCURACY_THRESHOLD. The level never regresses — below-threshold
performance only affects mastery_score/accuracy_window, never moves
cefr_level backward. A single miss inside an otherwise-strong window does
not reset progress, because the window is a sliding accuracy count, not a
consecutive-correct streak.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from shared_kernel.domain.enums import CEFRLevel

ACCURACY_WINDOW_MAX_SIZE = 10
MIN_ACTIVITIES_BEFORE_ADVANCE = 5
ADVANCEMENT_ACCURACY_THRESHOLD = 0.8

# Deterministic exact-match activities produce a natural 0.0/1.0
# performance_score; open-ended (agent-scored) turns and exercises produce
# a continuous 0..1 signal that must be thresholded into the windowed
# rule's boolean `correct` input. This constant is that threshold — a
# separate, independently-tunable domain-rule value, not the same number
# as ADVANCEMENT_ACCURACY_THRESHOLD (which governs the window, not a
# single attempt).
CORRECT_SCORE_THRESHOLD = 0.6

_LEVEL_ORDER: list[CEFRLevel] = [
    CEFRLevel.A1,
    CEFRLevel.A2,
    CEFRLevel.B1,
    CEFRLevel.B2,
    CEFRLevel.C1,
    CEFRLevel.C2,
]


@dataclass(frozen=True)
class AccuracyWindowEntry:
    correct: bool
    at: datetime


@dataclass(frozen=True)
class LevelAdvancementResult:
    cefr_level: CEFRLevel
    mastery_score: int
    accuracy_window: tuple[AccuracyWindowEntry, ...]
    level_advanced: bool


def next_level(level: CEFRLevel) -> CEFRLevel | None:
    """The CEFR level one step above `level`, or `None` if already at the
    ceiling (`C2` never advances further)."""
    idx = _LEVEL_ORDER.index(level)
    if idx + 1 >= len(_LEVEL_ORDER):
        return None
    return _LEVEL_ORDER[idx + 1]


def performance_score_is_correct(performance_score: float) -> bool:
    """Boolean `correct` input to the windowed-accuracy rule, derived from
    a continuous 0..1 `performance_score`."""
    return performance_score >= CORRECT_SCORE_THRESHOLD


def _accuracy(window: Sequence[AccuracyWindowEntry]) -> float:
    if not window:
        return 0.0
    return sum(1 for entry in window if entry.correct) / len(window)


def apply_scored_activity(
    *,
    cefr_level: CEFRLevel,
    mastery_score: int,
    accuracy_window: Sequence[AccuracyWindowEntry],
    correct: bool,
    at: datetime,
) -> LevelAdvancementResult:
    """Fold one newly-scored activity outcome into the windowed-accuracy
    rule and decide whether the skill's CEFR level advances.

    - Appends `(correct, at)` to `accuracy_window`, keeping only the most
      recent `ACCURACY_WINDOW_MAX_SIZE` entries (oldest dropped first).
    - Recomputes `mastery_score` as `round(accuracy * 100)` over the
      (updated) window.
    - Advances `cefr_level` one step when the window has at least
      `MIN_ACTIVITIES_BEFORE_ADVANCE` entries and accuracy is at least
      `ADVANCEMENT_ACCURACY_THRESHOLD`. On advance, `mastery_score` resets
      to 0 and `accuracy_window` clears (fresh tracking at the new level).
      Already at `C2`: no further advancement, even if criteria are met.
    """
    new_window = [*accuracy_window, AccuracyWindowEntry(correct=correct, at=at)]
    if len(new_window) > ACCURACY_WINDOW_MAX_SIZE:
        new_window = new_window[-ACCURACY_WINDOW_MAX_SIZE:]

    accuracy = _accuracy(new_window)
    new_mastery_score = round(accuracy * 100)

    result_level = cefr_level
    level_advanced = False
    enough_activities = len(new_window) >= MIN_ACTIVITIES_BEFORE_ADVANCE
    if enough_activities and accuracy >= ADVANCEMENT_ACCURACY_THRESHOLD:
        upgraded = next_level(cefr_level)
        if upgraded is not None:
            result_level = upgraded
            new_mastery_score = 0
            new_window = []
            level_advanced = True

    return LevelAdvancementResult(
        cefr_level=result_level,
        mastery_score=new_mastery_score,
        accuracy_window=tuple(new_window),
        level_advanced=level_advanced,
    )
