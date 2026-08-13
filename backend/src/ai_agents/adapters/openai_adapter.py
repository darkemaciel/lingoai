"""`OpenAIAdapter` (T067) — implements all three agent ports
(`AssessmentAgentPort`, `ConversationAgentPort`, `ProgressionSignalAgentPort`)
against the real OpenAI Chat Completions API, using forced function-calling
to get structured JSON output matching each port's Pydantic output shape
(contracts/agent-ports.md). Mirrors `anthropic_adapter.py`'s structure —
one class implementing all three ports, same shared prompt templates —
with only the provider-specific request/response shape differing (OpenAI's
`tools`/function-calling shape vs. Anthropic's `tool_use`, and the
`arguments` field arriving as a JSON *string* to parse rather than an
already-parsed dict).

Configuration: `OPENAI_API_KEY` env var (research.md §8, NFR-3). Logging
(`AgentInvocationLog`, NFR-4) is the caller's responsibility, same as every
other adapter (contracts/agent-ports.md).
"""

from __future__ import annotations

import json
import os
from typing import TypeVar

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageFunctionToolCall
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

DEFAULT_MODEL = "gpt-4o-mini"

_OutputT = TypeVar("_OutputT", bound=BaseModel)


class OpenAIAdapterConfigurationError(Exception):
    pass


class OpenAIAdapterResponseError(Exception):
    """Raised when the model doesn't return the forced tool call — should
    not happen given `tool_choice` forces exactly one, but this fails
    loudly rather than crashing on an `IndexError`/`AttributeError` if the
    API ever behaves unexpectedly."""


class OpenAIAdapter:
    """Real OpenAI-backed implementation of all three agent ports."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise OpenAIAdapterConfigurationError("OPENAI_API_KEY is not configured")
        self._client = AsyncOpenAI(api_key=resolved_key)
        self._model = model

    async def _call_structured(
        self, *, system: str, user_content: str, output_model: type[_OutputT], tool_name: str
    ) -> _OutputT:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": f"Emit the structured {tool_name} result.",
                        "parameters": output_model.model_json_schema(),
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls or not isinstance(tool_calls[0], ChatCompletionMessageFunctionToolCall):
            raise OpenAIAdapterResponseError(
                f"expected a function tool call for '{tool_name}', got none"
            )
        arguments = json.loads(tool_calls[0].function.arguments)
        return output_model.model_validate(arguments)

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
