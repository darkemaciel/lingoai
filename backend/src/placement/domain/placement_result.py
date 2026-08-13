"""``PlacementResult`` domain entity (placement module).

Pure Python — no SQLAlchemy/FastAPI imports (Constitution §3). Generated
once per completed `PlacementSession` (data-model.md), 1:1 via
`placement_session_id`.

Immutable once created: a re-placement, if ever supported, creates a new
`PlacementSession`/`PlacementResult` pair rather than editing this one, so
this class deliberately exposes no mutator methods. It still extends
`Entity` (like `PlacementSession`) rather than the frozen `ValueObject`
base, because it *has* identity (`id`, referenced 1:1 by
`placement_session_id`) even though its state never changes post-creation —
`ValueObject`'s structural (no-`id`) equality would be the wrong semantics
here. "No mutation" is therefore enforced by convention (no setters, only
a construction-time factory) rather than `frozen=True`, since `Entity`
itself is not frozen and Python dataclasses disallow mixing frozen and
non-frozen classes across an inheritance chain.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from placement.domain.placement_session import PlacementSession, PlacementSessionStatus
from shared_kernel.domain.base import Entity
from shared_kernel.domain.enums import CEFRLevel


class PlacementSessionNotCompletedError(Exception):
    """Raised by `PlacementResult.from_completed_session` when the given
    `PlacementSession.status` is not `completed`."""


@dataclass(eq=False)
class PlacementResult(Entity):
    """The per-skill CEFR outcome of a completed placement session.

    Construct via `PlacementResult.from_completed_session(...)` rather than
    the dataclass constructor directly, except when rehydrating from
    persistence (T027).
    """

    placement_session_id: uuid.UUID = field(kw_only=True)
    reading_level: CEFRLevel = field(kw_only=True)
    writing_level: CEFRLevel = field(kw_only=True)
    speaking_level: CEFRLevel | None = field(kw_only=True)
    listening_level: CEFRLevel | None = field(kw_only=True)
    strengths_summary: str = field(kw_only=True)
    weaknesses_summary: str = field(kw_only=True)
    generated_at: datetime = field(kw_only=True)

    @classmethod
    def from_completed_session(
        cls,
        session: PlacementSession,
        *,
        reading_level: CEFRLevel,
        writing_level: CEFRLevel,
        speaking_level: CEFRLevel | None,
        listening_level: CEFRLevel | None,
        strengths_summary: str,
        weaknesses_summary: str,
    ) -> PlacementResult:
        """Factory: only constructible from a `session` whose
        `status == PlacementSessionStatus.COMPLETED`. `speaking_level`/
        `listening_level` are expected to be `None` when no audio modality
        was used (FR-3) — the caller (T028) decides that, this factory does
        not re-derive it from `session.modality`.

        Raises `PlacementSessionNotCompletedError` otherwise.
        """
        if session.status != PlacementSessionStatus.COMPLETED:
            raise PlacementSessionNotCompletedError(
                f"cannot generate a PlacementResult from PlacementSession "
                f"'{session.id}' in status '{session.status}' "
                "(session must be 'completed')"
            )
        return cls(
            id=uuid.uuid4(),
            placement_session_id=session.id,
            reading_level=reading_level,
            writing_level=writing_level,
            speaking_level=speaking_level,
            listening_level=listening_level,
            strengths_summary=strengths_summary,
            weaknesses_summary=weaknesses_summary,
            generated_at=datetime.now(UTC),
        )
