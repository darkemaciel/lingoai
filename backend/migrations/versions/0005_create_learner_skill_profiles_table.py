"""create learner_skill_profiles table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The "skill" enum type was created by 0002_create_learning_events_table
# and is intentionally REUSED here (create_type=False, not created/dropped
# by this migration) so LearningEvent.skill and LearnerSkillProfile.skill
# share one Postgres enum type rather than two divergent ones — see the
# comment in 0002 and shared_kernel/domain/enums.py.
_SKILL = postgresql.ENUM(
    "reading",
    "writing",
    "speaking",
    "listening",
    name="skill",
    create_type=False,
)

# New enum, owned/created/dropped by this migration. Backs the shared
# `shared_kernel.domain.enums.CEFRLevel` — reused (not recreated) by any
# future migration that adds a `cefr_level` column elsewhere (e.g. a future
# placement.PlacementResult table), the same pattern as the `skill` enum
# owned by 0002.
_CEFR_LEVEL = postgresql.ENUM(
    "A1",
    "A2",
    "B1",
    "B2",
    "C1",
    "C2",
    name="cefr_level",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _CEFR_LEVEL.create(bind, checkfirst=True)

    op.create_table(
        "learner_skill_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("skill", _SKILL, nullable=False),
        sa.Column("cefr_level", _CEFR_LEVEL, nullable=False),
        sa.Column("mastery_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "accuracy_window",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "skill",
            name="uq_learner_skill_profiles_user_skill",
        ),
    )
    op.create_index("ix_learner_skill_profiles_user_id", "learner_skill_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_learner_skill_profiles_user_id", table_name="learner_skill_profiles")
    op.drop_table("learner_skill_profiles")

    bind = op.get_bind()
    _CEFR_LEVEL.drop(bind, checkfirst=True)
    # _SKILL is NOT dropped here — it's owned by 0002, still in use by
    # learning_events.skill.
