"""Contract test (T062): `AnthropicAdapter` against hand-authored fixture
payloads — research.md §9 explicitly sanctions "vcrpy-style recorded
cassettes (**or hand-authored fixture payloads** for pure-unit agent
tests)"; no `vcrpy`/cassette-recording dependency exists in this project
yet, and this codebase has no `ANTHROPIC_API_KEY` to record a real cassette
against, so this suite mocks the Anthropic SDK's `messages.create` call
directly with a fixture-shaped response and asserts the adapter parses it
into the same contract shape `LocalModelAdapter` already proves
(contracts/agent-ports.md's "every adapter is tested against the same
contract test suite" — same *shape* assertions, fixture-driven instead of
canned-deterministic since this adapter has no built-in determinism of its
own). Never makes a real network call (NFR-7).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic.types import ToolUseBlock

from ai_agents.adapters.anthropic_adapter import (
    AnthropicAdapter,
    AnthropicAdapterConfigurationError,
)
from ai_agents.ports.assessment_agent_port import AssessmentTurnInput
from ai_agents.ports.conversation_agent_port import ConversationTurnInput, LearnerContext
from ai_agents.ports.progression_signal_agent_port import ProgressionSignalInput


def _tool_use_response(input_payload: dict) -> SimpleNamespace:
    """A minimal stand-in for `anthropic.types.Message`, using a real
    `ToolUseBlock` (so `AnthropicAdapter._call_structured`'s `isinstance`
    narrowing exercises the actual SDK type) wrapped in a bare namespace
    for the rest of the `Message` shape this adapter doesn't touch."""
    block = ToolUseBlock(
        type="tool_use", id=str(uuid.uuid4()), name="test_tool", input=input_payload
    )
    return SimpleNamespace(content=[block])


@pytest.fixture
def adapter() -> AnthropicAdapter:
    instance = AnthropicAdapter(api_key="test-key")
    instance._client.messages.create = AsyncMock()  # type: ignore[method-assign]
    return instance


class TestAnthropicAdapterConfiguration:
    def test_raises_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AnthropicAdapterConfigurationError):
            AnthropicAdapter()


class TestAnthropicAdapterContract:
    async def test_process_turn_matches_assessment_contract_shape(
        self, adapter: AnthropicAdapter
    ) -> None:
        adapter._client.messages.create.return_value = _tool_use_response(
            {
                "next_prompt_text": None,
                "is_complete": True,
                "skill_signals": {
                    "reading": {"cefr_level": "B1", "confidence": 0.8},
                    "writing": {"cefr_level": "B1", "confidence": 0.75},
                    "speaking": None,
                    "listening": None,
                },
                "strengths_summary": "Clear, simple sentence structure.",
                "weaknesses_summary": "Limited vocabulary range.",
            }
        )
        output = await adapter.process_turn(
            AssessmentTurnInput(conversation_so_far=[], latest_student_response="Hello!")
        )
        assert output.is_complete is True
        assert output.skill_signals is not None
        assert output.skill_signals.reading.cefr_level == "B1"
        assert output.skill_signals.speaking is None

    async def test_process_message_matches_conversation_contract_shape(
        self, adapter: AnthropicAdapter
    ) -> None:
        adapter._client.messages.create.return_value = _tool_use_response(
            {
                "reply_text": "Nice! Tell me more.",
                "scored": True,
                "skill": "writing",
                "performance_score": 0.7,
                "feedback_text": "Good sentence variety.",
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
        assert output.scored is True
        assert 0.0 <= output.performance_score <= 1.0
        assert output.feedback_text

    async def test_evaluate_matches_progression_signal_contract_shape(
        self, adapter: AnthropicAdapter
    ) -> None:
        adapter._client.messages.create.return_value = _tool_use_response(
            {"performance_score": 0.9, "feedback_text": "Well done, thorough response."}
        )
        output = await adapter.evaluate(
            ProgressionSignalInput(
                activity_prompt="Describe your morning routine.",
                student_response="I wake up, brush my teeth, and eat breakfast.",
                rubric={"expected_min_words": 5},
            )
        )
        assert 0.0 <= output.performance_score <= 1.0
        assert output.feedback_text
