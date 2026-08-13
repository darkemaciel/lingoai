"""Port contract for the Conversation agent.

Used by the ``conversation`` module for the ongoing post-placement
learning-loop conversation (see
specs/001-placement-learning-loop/contracts/agent-ports.md).

Contract rule: the agent never decides XP, level advancement, or streak — it
only emits ``performance_score``/``feedback_text`` as a *signal*. The
``progression`` and ``gamification`` modules consume the resulting
``LearningEvent`` independently (FR-9, FR-18).
"""

from typing import Protocol

from pydantic import BaseModel

from ai_agents.ports.assessment_agent_port import ConversationTurnMessage


class LearnerSkillSnapshot(BaseModel):
    """Read-only snapshot of one skill's current state for agent context."""

    skill: str
    cefr_level: str
    mastery_score: int


class LearnerContext(BaseModel):
    """Read-only learner context, never mutated by the agent."""

    skills: list[LearnerSkillSnapshot]


class ConversationTurnInput(BaseModel):
    """Input to one post-placement conversation turn."""

    conversation_history: list[ConversationTurnMessage]
    student_message: str
    # Already transcribed by SpeechToTextProvider if this turn was audio.
    audio_transcript: str | None = None
    learner_context: LearnerContext


class ConversationTurnOutput(BaseModel):
    """Output of one post-placement conversation turn."""

    reply_text: str
    # Whether this turn should produce a LearningEvent.
    scored: bool
    # Which skill this turn evaluated, if scored=True.
    skill: str | None = None
    # 0..1, only if scored=True.
    performance_score: float | None = None
    # Pedagogical feedback (FR-8), only if scored=True.
    feedback_text: str | None = None


class ConversationAgentPort(Protocol):
    """Structural interface implemented by every conversation-agent adapter.

    Named ``process_message`` (rather than ``process_turn``, as used by
    ``AssessmentAgentPort``) so a single adapter class can implement both
    ``AssessmentAgentPort`` and ``ConversationAgentPort`` without a
    same-name/different-signature method collision (see
    ``adapters/local_model_adapter.py``).
    """

    async def process_message(self, input: ConversationTurnInput) -> ConversationTurnOutput:
        """Advance the learning-loop conversation by one turn."""
        ...
