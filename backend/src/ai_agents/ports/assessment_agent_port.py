"""Port contract for the Assessment/Leveling agent.

Used by the ``placement`` module during a ``PlacementSession`` (see
specs/001-placement-learning-loop/contracts/agent-ports.md).

Contract rule: ``skill_signals`` are *inputs* to ``PlacementResult`` creation,
not the final decision — the ``placement`` application service persists them
verbatim into ``PlacementResult`` (this is the one agent whose signal *is*
directly the placement outcome, since there is no prior state to reconcile
against, unlike the Progression signal).
"""

from typing import Literal, Protocol

from pydantic import BaseModel


class ConversationTurnMessage(BaseModel):
    """One turn of the conversation-so-far transcript fed to an agent."""

    sender: Literal["student", "agent"]
    text: str


class SkillSignal(BaseModel):
    """A single skill's assessed CEFR level and the agent's confidence in it."""

    cefr_level: str
    confidence: float


class SkillSignals(BaseModel):
    """Per-skill signals, only fully populated once ``is_complete=True``.

    ``speaking``/``listening`` remain ``None`` when there is no audio
    modality in play for this placement session.
    """

    reading: SkillSignal | None = None
    writing: SkillSignal | None = None
    speaking: SkillSignal | None = None
    listening: SkillSignal | None = None


class AssessmentTurnInput(BaseModel):
    """Input to one placement-conversation turn."""

    conversation_so_far: list[ConversationTurnMessage]
    latest_student_response: str
    # Already transcribed by SpeechToTextProvider if this turn was audio.
    audio_transcript: str | None = None


class AssessmentTurnOutput(BaseModel):
    """Output of one placement-conversation turn."""

    # None signals placement is complete.
    next_prompt_text: str | None
    is_complete: bool
    # Only populated once is_complete=True.
    skill_signals: SkillSignals | None = None
    strengths_summary: str | None = None
    weaknesses_summary: str | None = None


class AssessmentAgentPort(Protocol):
    """Structural interface implemented by every assessment-agent adapter."""

    async def process_turn(self, input: AssessmentTurnInput) -> AssessmentTurnOutput:
        """Advance the placement conversation by one turn."""
        ...
