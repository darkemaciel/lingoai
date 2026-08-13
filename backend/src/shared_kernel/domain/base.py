"""Base domain building blocks (``Entity``, ``ValueObject``) shared across
every bounded context.

Pure Python — no framework/ORM/DB dependency (Constitution §3: the Domain
layer must not depend on Infrastructure). SQLAlchemy models living in each
module's ``infrastructure/`` layer are separate classes that *map* domain
concepts to tables; they do not have to inherit from these.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(eq=False)
class Entity:
    """Base class for domain entities.

    Entities are compared by identity (``id``), not by attribute values —
    two entities with the same id are "the same thing" even if their other
    fields have since diverged in memory.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))


@dataclass(frozen=True)
class ValueObject:
    """Base class for domain value objects.

    Value objects are immutable (``frozen=True``) and compared structurally
    — ``dataclass`` generates ``__eq__`` from field values automatically, so
    subclasses get value-based equality for free as long as they stay frozen
    dataclasses themselves.
    """
