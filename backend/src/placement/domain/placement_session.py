"""``PlacementSession`` domain entity (placement module).

Pure Python — no SQLAlchemy/FastAPI imports (Constitution §3: the Domain
layer must be framework-independent; ``backend/src/placement/infrastructure/``
maps this entity to a table separately, per T027).

Per data-model.md's PlacementSession state-transition rule: a session is
created ``in_progress`` and moves to exactly one terminal state —
``completed`` (normal path) or ``abandoned`` (inactivity timeout, or an
explicit student restart). Terminal states never transition again; a
restart creates a brand new session rather than resurrecting the old one,
so there is deliberately no "reopen"/"resume" method here.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from shared_kernel.domain.base import Entity


class PlacementSessionStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class PlacementModality(enum.StrEnum):
    """Reflects whether audio was actually *used* during the session (FR-3,
    edge case: no mic available) — not merely what was offered/attempted."""

    TEXT_ONLY = "text_only"
    TEXT_AND_AUDIO = "text_and_audio"


class InvalidPlacementSessionTransitionError(Exception):
    """Raised when `complete()`/`abandon()` is called on a session that is
    already in a terminal state (`completed` or `abandoned`)."""


@dataclass(eq=False)
class PlacementSession(Entity):
    """A student's in-progress or finished placement (nivelamento) attempt.

    Construct via `PlacementSession.start(...)` rather than the dataclass
    constructor directly, except when rehydrating from persistence (T027),
    where all fields — including a previously generated `id` — are known.
    """

    user_id: uuid.UUID = field(kw_only=True)
    status: PlacementSessionStatus = field(kw_only=True)
    modality: PlacementModality = field(kw_only=True)
    started_at: datetime = field(kw_only=True)
    completed_at: datetime | None = field(default=None, kw_only=True)

    @classmethod
    def start(cls, user_id: uuid.UUID, modality: PlacementModality) -> PlacementSession:
        """Factory for a freshly started session: generates `id`, stamps
        `started_at` at now (UTC), and sets `status = in_progress`."""
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            status=PlacementSessionStatus.IN_PROGRESS,
            modality=modality,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

    @property
    def is_terminal(self) -> bool:
        """True once the session has reached `completed` or `abandoned` —
        callers (e.g. the application service, T028) can use this to guard
        further answer submissions without duplicating the status check."""
        return self.status in (
            PlacementSessionStatus.COMPLETED,
            PlacementSessionStatus.ABANDONED,
        )

    def complete(self) -> None:
        """Transition `in_progress -> completed`, stamping `completed_at`.

        Raises `InvalidPlacementSessionTransitionError` if the session is
        already in a terminal state.
        """
        if self.status != PlacementSessionStatus.IN_PROGRESS:
            raise InvalidPlacementSessionTransitionError(
                f"cannot complete a PlacementSession in status '{self.status}' "
                "(only 'in_progress' sessions can be completed)"
            )
        self.status = PlacementSessionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def abandon(self) -> None:
        """Transition `in_progress -> abandoned` (inactivity timeout or an
        explicit student restart, per data-model.md). `completed_at` stays
        `None` — it is only ever set on the `completed` path.

        Raises `InvalidPlacementSessionTransitionError` if the session is
        already in a terminal state.
        """
        if self.status != PlacementSessionStatus.IN_PROGRESS:
            raise InvalidPlacementSessionTransitionError(
                f"cannot abandon a PlacementSession in status '{self.status}' "
                "(only 'in_progress' sessions can be abandoned)"
            )
        self.status = PlacementSessionStatus.ABANDONED
