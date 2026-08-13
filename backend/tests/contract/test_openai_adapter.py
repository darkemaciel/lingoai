"""Contract test (T063): `OpenAIAdapter` against hand-authored fixture
payloads — same rationale as `test_anthropic_adapter.py` (research.md §9's
sanctioned alternative to vcrpy cassettes; no API key/cassette-recording
setup available in this environment). Mocks the OpenAI SDK's
`chat.completions.create` call directly; never makes a real network call
(NFR-7).
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_function_tool_call import Function

from ai_agents.adapters.openai_adapter import OpenAIAdapter, OpenAIAdapterConfigurationError
from ai_agents.ports.assessment_agent_port import AssessmentTurnInput
from ai_agents.ports.conversation_agent_port import ConversationTurnInput, LearnerContext
from ai_agents.ports.progression_signal_agent_port import ProgressionSignalInput


def _tool_call_response(arguments: dict) -> SimpleNamespace:
    """A minimal stand-in for `openai.types.chat.ChatCompletion`, using a
    real `ChatCompletionMessageFunctionToolCall` (so `OpenAIAdapter.
    _call_structured`'s `isinstance` narrowing exercises the actual SDK
    type) wrapped in bare namespaces for the rest of the response shape
    this adapter doesn't touch."""
    tool_call = ChatCompletionMessageFunctionToolCall(
        id=str(uuid.uuid4()),
        type="function",
        function=Function(name="test_tool", arguments=json.dumps(arguments)),
    )
    message = SimpleNamespace(tool_calls=[tool_call])
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


@pytest.fixture
def adapter() -> OpenAIAdapter:
    instance = OpenAIAdapter(api_key="test-key")
    instance._client.chat.completions.create = AsyncMock()  # type: ignore[method-assign]
    return instance


class TestOpenAIAdapterConfiguration:
    def test_raises_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(OpenAIAdapterConfigurationError):
            OpenAIAdapter()


class TestOpenAIAdapterContract:
    async def test_process_turn_matches_assessment_contract_shape(
        self, adapter: OpenAIAdapter
    ) -> None:
        adapter._client.chat.completions.create.return_value = _tool_call_response(
            {
                "next_prompt_text": "Describe your daily routine.",
                "is_complete": False,
                "skill_signals": None,
                "strengths_summary": None,
                "weaknesses_summary": None,
            }
        )
        output = await adapter.process_turn(
            AssessmentTurnInput(conversation_so_far=[], latest_student_response="Hello!")
        )
        assert output.is_complete is False
        assert output.next_prompt_text
        assert output.skill_signals is None

    async def test_process_message_matches_conversation_contract_shape(
        self, adapter: OpenAIAdapter
    ) -> None:
        adapter._client.chat.completions.create.return_value = _tool_call_response(
            {
                "reply_text": "Great, keep going!",
                "scored": False,
                "skill": None,
                "performance_score": None,
                "feedback_text": None,
            }
        )
        output = await adapter.process_message(
            ConversationTurnInput(
                conversation_history=[],
                student_message="I went to the market.",
                audio_transcript=None,
                learner_context=LearnerContext(skills=[]),
            )
        )
        assert output.scored is False
        assert output.performance_score is None
        assert output.reply_text

    async def test_evaluate_matches_progression_signal_contract_shape(
        self, adapter: OpenAIAdapter
    ) -> None:
        adapter._client.chat.completions.create.return_value = _tool_call_response(
            {"performance_score": 0.55, "feedback_text": "Good attempt, add more detail."}
        )
        output = await adapter.evaluate(
            ProgressionSignalInput(
                activity_prompt="Describe your morning routine.",
                student_response="I wake up early.",
                rubric={"expected_min_words": 5},
            )
        )
        assert 0.0 <= output.performance_score <= 1.0
        assert output.feedback_text
