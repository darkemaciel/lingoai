"""Port contract for the Progression Signal agent.

Used by the ``progression`` module only for activity types where correctness
isn't purely rule-based (e.g., open-ended writing/speaking responses need an
LLM judgment before the deterministic domain rule can run).
Multiple-choice/exact-match exercises skip this port entirely and go
straight to the deterministic rule (see
specs/001-placement-learning-loop/contracts/agent-ports.md).

Contract rule (Constitution §1, §5 — the load-bearing one): this port's
output is *only* a signal. The actual level-advancement decision is
computed by the deterministic domain rule in ``progression/domain/``
(windowed accuracy >= 80% over last 10), which is pure Python, has no
dependency on this port, and is unit-tested without any agent/LLM involved
(NFR-7, AC-4).
"""

from typing import Any, Protocol

from pydantic import BaseModel


class ProgressionSignalInput(BaseModel):
    """Input asking the agent to judge one open-ended student response."""

    activity_prompt: str
    student_response: str
    # From Activity.prompt_content.
    rubric: dict[str, Any]


class ProgressionSignalOutput(BaseModel):
    """The agent's judgment signal for one open-ended student response."""

    # 0..1.
    performance_score: float
    feedback_text: str


class ProgressionSignalAgentPort(Protocol):
    """Structural interface implemented by every progression-signal adapter."""

    async def evaluate(self, input: ProgressionSignalInput) -> ProgressionSignalOutput:
        """Produce a performance-score signal for one open-ended response."""
        ...
