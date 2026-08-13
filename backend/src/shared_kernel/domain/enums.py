"""Domain enums shared across multiple bounded contexts.

Kept in ``shared_kernel`` (rather than duplicated per module) because both
``LearningEvent`` (this module) and ``LearnerSkillProfile`` (progression
module, introduced later) need the exact same four-value ``Skill`` vocabulary
per data-model.md — and because the Postgres enum type ``skill`` created by
the ``LearningEvent`` migration is reused (not recreated) by later
migrations that add a ``skill`` column.

``CEFRLevel`` is kept here for the same reason: per data-model.md,
``PlacementResult`` (placement module, T024) and ``LearnerSkillProfile``
(progression module, T025) both need the identical six-value CEFR
vocabulary (``A1``..``C2``), and a single shared Postgres enum type avoids
two independent migrations defining overlapping ``a1``..``c2`` enum types.
"""

from __future__ import annotations

import enum


class Skill(enum.StrEnum):
    READING = "reading"
    WRITING = "writing"
    SPEAKING = "speaking"
    LISTENING = "listening"


class CEFRLevel(enum.StrEnum):
    """Common European Framework of Reference proficiency levels.

    Used by ``PlacementResult.reading_level``/``writing_level``/
    ``speaking_level``/``listening_level`` and (later)
    ``LearnerSkillProfile.cefr_level`` per data-model.md.
    """

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class ActivityType(enum.StrEnum):
    """Shared across ``learning_content`` (``Activity.type``),
    ``conversation`` (ad hoc, non-Activity-backed conversation turns are
    tagged ``CONVERSATION_PROMPT`` too — data-model.md's Activity table
    notes this type "drives base_xp lookup", and research.md §7's "conversation
    turn" XP rate is exactly this case) and ``gamification`` (XP base-rate
    table, research.md §7).
    """

    CONVERSATION_PROMPT = "conversation_prompt"
    WRITING_EXERCISE = "writing_exercise"
    SPEAKING_EXERCISE = "speaking_exercise"
    LISTENING_EXERCISE = "listening_exercise"
