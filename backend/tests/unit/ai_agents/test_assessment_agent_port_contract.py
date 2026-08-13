"""Contract test (T020): AssessmentAgentPort via LocalModelAdapter matches
the input/output shape documented in contracts/agent-ports.md. Runs
against LocalModelAdapter only (NFR-7 — no live LLM in unit tests);
Anthropic/OpenAI adapters get an equivalent cassette-based contract test
later (T062/T063, User Story 3), parameterized against this same shape.
"""

from __future__ import annotations

import pytest

from ai_agents.adapters.local_model_adapter import (
    ASSESSMENT_TURNS_BEFORE_COMPLETE,
    LocalModelAdapter,
)
from ai_agents.ports.assessment_agent_port import (
    AssessmentTurnInput,
    AssessmentTurnOutput,
    ConversationTurnMessage,
)


@pytest.fixture
def adapter() -> LocalModelAdapter:
    return LocalModelAdapter()


class TestAssessmentAgentPortContract:
    async def test_incomplete_turn_returns_next_prompt_and_no_signals(
        self, adapter: LocalModelAdapter
    ) -> None:
        output = await adapter.process_turn(
            AssessmentTurnInput(conversation_so_far=[], latest_student_response="Hello!")
        )
        assert isinstance(output, AssessmentTurnOutput)
        assert output.is_complete is False
        assert output.next_prompt_text is not None
        assert isinstance(output.next_prompt_text, str)
        assert output.skill_signals is None
        assert output.strengths_summary is None
        assert output.weaknesses_summary is None

    async def test_final_turn_completes_with_full_skill_signals_when_audio_used(
        self, adapter: LocalModelAdapter
    ) -> None:
        conversation_so_far = [
            ConversationTurnMessage(sender="student", text=f"turn {i}")
            for i in range(ASSESSMENT_TURNS_BEFORE_COMPLETE - 1)
        ]
        output = await adapter.process_turn(
            AssessmentTurnInput(
                conversation_so_far=conversation_so_far,
                latest_student_response="final answer",
                audio_transcript="some transcribed audio",
            )
        )
        assert output.is_complete is True
        assert output.next_prompt_text is None
        assert output.skill_signals is not None
        # Per the contract: reading/writing always populated; speaking/
        # listening only when audio was used.
        assert output.skill_signals.reading is not None
        assert output.skill_signals.writing is not None
        assert output.skill_signals.speaking is not None
        assert output.skill_signals.listening is not None
        for signal in (
            output.skill_signals.reading,
            output.skill_signals.writing,
            output.skill_signals.speaking,
            output.skill_signals.listening,
        ):
            assert 0.0 <= signal.confidence <= 1.0
            assert isinstance(signal.cefr_level, str)
        assert isinstance(output.strengths_summary, str)
        assert isinstance(output.weaknesses_summary, str)

    async def test_final_turn_without_audio_leaves_speaking_listening_none(
        self, adapter: LocalModelAdapter
    ) -> None:
        conversation_so_far = [
            ConversationTurnMessage(sender="student", text=f"turn {i}")
            for i in range(ASSESSMENT_TURNS_BEFORE_COMPLETE - 1)
        ]
        output = await adapter.process_turn(
            AssessmentTurnInput(
                conversation_so_far=conversation_so_far,
                latest_student_response="final answer",
                audio_transcript=None,
            )
        )
        assert output.is_complete is True
        assert output.skill_signals.speaking is None
        assert output.skill_signals.listening is None

    async def test_deterministic_for_identical_input(self, adapter: LocalModelAdapter) -> None:
        turn_input = AssessmentTurnInput(conversation_so_far=[], latest_student_response="hi")
        first = await adapter.process_turn(turn_input)
        second = await adapter.process_turn(turn_input)
        assert first == second
