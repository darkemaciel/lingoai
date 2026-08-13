"""Contract test (T038): `ConversationAgentPort` and
`ProgressionSignalAgentPort` via `LocalModelAdapter` match the input/output
shapes documented in contracts/agent-ports.md. Runs against
`LocalModelAdapter` only (NFR-7 — no live LLM in unit tests); Anthropic/
OpenAI adapters get an equivalent cassette-based contract test later
(T062/T063, User Story 3).
"""

from __future__ import annotations

import pytest

from ai_agents.adapters.local_model_adapter import LocalModelAdapter
from ai_agents.ports.assessment_agent_port import ConversationTurnMessage
from ai_agents.ports.conversation_agent_port import (
    ConversationTurnInput,
    ConversationTurnOutput,
    LearnerContext,
    LearnerSkillSnapshot,
)
from ai_agents.ports.progression_signal_agent_port import (
    ProgressionSignalInput,
    ProgressionSignalOutput,
)


@pytest.fixture
def adapter() -> LocalModelAdapter:
    return LocalModelAdapter()


class TestConversationAgentPortContract:
    async def test_unscored_turn_has_no_signal_fields(self, adapter: LocalModelAdapter) -> None:
        # Empty history -> len(history) % 2 == 0 -> scored=True per the
        # adapter's own docstring; use a 1-message history for the
        # unscored (odd) branch instead.
        output = await adapter.process_message(
            ConversationTurnInput(
                conversation_history=[ConversationTurnMessage(sender="agent", text="Hi!")],
                student_message="Hello",
                audio_transcript=None,
                learner_context=LearnerContext(skills=[]),
            )
        )
        assert isinstance(output, ConversationTurnOutput)
        assert output.scored is False
        assert output.skill is None
        assert output.performance_score is None
        assert output.feedback_text is None
        assert isinstance(output.reply_text, str) and output.reply_text

    async def test_scored_turn_has_all_signal_fields_populated(
        self, adapter: LocalModelAdapter
    ) -> None:
        output = await adapter.process_message(
            ConversationTurnInput(
                conversation_history=[],
                student_message="I went to the market and bought fresh vegetables yesterday.",
                audio_transcript=None,
                learner_context=LearnerContext(
                    skills=[
                        LearnerSkillSnapshot(skill="writing", cefr_level="B1", mastery_score=40)
                    ]
                ),
            )
        )
        assert output.scored is True
        assert output.skill == "writing"
        assert output.performance_score is not None
        assert 0.0 <= output.performance_score <= 1.0
        assert isinstance(output.feedback_text, str) and output.feedback_text

    async def test_scored_turn_without_learner_context_defaults_skill(
        self, adapter: LocalModelAdapter
    ) -> None:
        output = await adapter.process_message(
            ConversationTurnInput(
                conversation_history=[],
                student_message="Hi",
                audio_transcript=None,
                learner_context=LearnerContext(skills=[]),
            )
        )
        assert output.scored is True
        assert output.skill == "conversation"

    async def test_deterministic_for_identical_input(self, adapter: LocalModelAdapter) -> None:
        turn_input = ConversationTurnInput(
            conversation_history=[],
            student_message="Good morning!",
            audio_transcript=None,
            learner_context=LearnerContext(skills=[]),
        )
        first = await adapter.process_message(turn_input)
        second = await adapter.process_message(turn_input)
        assert first == second


class TestProgressionSignalAgentPortContract:
    async def test_output_shape_and_score_range(self, adapter: LocalModelAdapter) -> None:
        output = await adapter.evaluate(
            ProgressionSignalInput(
                activity_prompt="Describe your morning routine.",
                student_response="I wake up, brush my teeth, and eat breakfast every day.",
                rubric={"expected_min_words": 5},
            )
        )
        assert isinstance(output, ProgressionSignalOutput)
        assert 0.0 <= output.performance_score <= 1.0
        assert isinstance(output.feedback_text, str) and output.feedback_text

    async def test_keyword_rubric_scores_by_keyword_coverage(
        self, adapter: LocalModelAdapter
    ) -> None:
        output = await adapter.evaluate(
            ProgressionSignalInput(
                activity_prompt="Name two fruits.",
                student_response="I like apples and bananas.",
                rubric={"keywords": ["apple", "banana", "orange"]},
            )
        )
        assert output.performance_score == pytest.approx(2 / 3)

    async def test_score_is_clamped_to_one(self, adapter: LocalModelAdapter) -> None:
        output = await adapter.evaluate(
            ProgressionSignalInput(
                activity_prompt="Write a long paragraph.",
                student_response=" ".join(["word"] * 50),
                rubric={"expected_min_words": 5},
            )
        )
        assert output.performance_score == 1.0

    async def test_deterministic_for_identical_input(self, adapter: LocalModelAdapter) -> None:
        signal_input = ProgressionSignalInput(
            activity_prompt="p", student_response="r", rubric={"expected_min_words": 2}
        )
        first = await adapter.evaluate(signal_input)
        second = await adapter.evaluate(signal_input)
        assert first == second
