"""`AnthropicAdapter` (T066) — implements all three agent ports
(`AssessmentAgentPort`, `ConversationAgentPort`, `ProgressionSignalAgentPort`)
against the real Anthropic Messages API, using forced tool-use to get
structured JSON output matching each port's Pydantic output shape
(contracts/agent-ports.md). One class implements all three ports, mirroring
`LocalModelAdapter`'s precedent (a single provider backend, not three
independently swappable ones).

Configuration: `ANTHROPIC_API_KEY` env var (research.md §8, NFR-3 — no
hardcoded secrets); construction fails fast if it's unset, so a
misconfigured `AI_PROVIDER=anthropic` never silently falls back to
something else. Logging (`AgentInvocationLog`, NFR-4) is the caller's
responsibility via `log_agent_invocation` at each application-service call
site (contracts/agent-ports.md: adapters don't implement logging
themselves) — this module makes no logging calls of its own.
"""

from __future__ import annotations

import os
from typing import TypeVar

from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock
from pydantic import BaseModel

from ai_agents.adapters.prompt_templates import (
    ASSESSMENT_SYSTEM_PROMPT,
    CONVERSATION_SYSTEM_PROMPT,
    PROGRESSION_SIGNAL_SYSTEM_PROMPT,
    assessment_user_content,
    conversation_user_content,
    progression_signal_user_content,
)
from ai_agents.ports.assessment_agent_port import AssessmentTurnInput, AssessmentTurnOutput
from ai_agents.ports.conversation_agent_port import ConversationTurnInput, ConversationTurnOutput
from ai_agents.ports.progression_signal_agent_port import (
    ProgressionSignalInput,
    ProgressionSignalOutput,
)

DEFAULT_MODEL = "claude-3-5-sonnet-latest"
_MAX_TOKENS = 1024

_OutputT = TypeVar("_OutputT", bound=BaseModel)


class AnthropicAdapterConfigurationError(Exception):
    pass


class AnthropicAdapter:
    """Real Anthropic-backed implementation of all three agent ports."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise AnthropicAdapterConfigurationError("ANTHROPIC_API_KEY is not configured")
        self._client = AsyncAnthropic(api_key=resolved_key)
        self._model = model

    async def _call_structured(
        self, *, system: str, user_content: str, output_model: type[_OutputT], tool_name: str
    ) -> _OutputT:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[
                {
                    "name": tool_name,
                    "description": f"Emit the structured {tool_name} result.",
                    "input_schema": output_model.model_json_schema(),
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
        tool_use_block = next(
            block for block in response.content if isinstance(block, ToolUseBlock)
        )
        return output_model.model_validate(tool_use_block.input)

    # ------------------------------------------------------------------
    # AssessmentAgentPort
    # ------------------------------------------------------------------
    async def process_turn(self, input: AssessmentTurnInput) -> AssessmentTurnOutput:
        return await self._call_structured(
            system=ASSESSMENT_SYSTEM_PROMPT,
            user_content=assessment_user_content(input),
            output_model=AssessmentTurnOutput,
            tool_name="emit_assessment_turn_output",
        )

    # ------------------------------------------------------------------
    # ConversationAgentPort
    # ------------------------------------------------------------------
    async def process_message(self, input: ConversationTurnInput) -> ConversationTurnOutput:
        return await self._call_structured(
            system=CONVERSATION_SYSTEM_PROMPT,
            user_content=conversation_user_content(input),
            output_model=ConversationTurnOutput,
            tool_name="emit_conversation_turn_output",
        )

    # ------------------------------------------------------------------
    # ProgressionSignalAgentPort
    # ------------------------------------------------------------------
    async def evaluate(self, input: ProgressionSignalInput) -> ProgressionSignalOutput:
        return await self._call_structured(
            system=PROGRESSION_SIGNAL_SYSTEM_PROMPT,
            user_content=progression_signal_user_content(input),
            output_model=ProgressionSignalOutput,
            tool_name="emit_progression_signal_output",
        )
