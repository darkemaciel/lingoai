"""Unit test (T019): PlacementResult derivation from AssessmentAgentPort
output — skill_signals -> persisted CEFR levels. Pure, no DB/agent needed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from ai_agents.ports.assessment_agent_port import SkillSignal, SkillSignals
from placement.application.placement_service import skill_signal_to_cefr_level
from placement.domain.placement_result import (
    PlacementResult,
    PlacementSessionNotCompletedError,
)
from placement.domain.placement_session import (
    PlacementModality,
    PlacementSession,
)
from shared_kernel.domain.enums import CEFRLevel


class TestSkillSignalToCefrLevel:
    def test_present_signal_maps_to_its_cefr_level(self) -> None:
        signal = SkillSignal(cefr_level="B1", confidence=0.7)
        assert skill_signal_to_cefr_level(signal) is CEFRLevel.B1

    def test_none_signal_maps_to_none(self) -> None:
        assert skill_signal_to_cefr_level(None) is None

    def test_every_cefr_level_string_round_trips(self) -> None:
        for level in CEFRLevel:
            signal = SkillSignal(cefr_level=level.value, confidence=0.5)
            assert skill_signal_to_cefr_level(signal) is level


class TestPlacementResultFromCompletedSession:
    def _completed_session(self) -> PlacementSession:
        session = PlacementSession.start(uuid.uuid4(), PlacementModality.TEXT_AND_AUDIO)
        session.complete()
        return session

    def test_full_skill_signals_persist_all_four_levels(self) -> None:
        session = self._completed_session()
        signals = SkillSignals(
            reading=SkillSignal(cefr_level="B1", confidence=0.7),
            writing=SkillSignal(cefr_level="B1", confidence=0.7),
            speaking=SkillSignal(cefr_level="A2", confidence=0.6),
            listening=SkillSignal(cefr_level="A2", confidence=0.6),
        )
        result = PlacementResult.from_completed_session(
            session,
            reading_level=skill_signal_to_cefr_level(signals.reading),
            writing_level=skill_signal_to_cefr_level(signals.writing),
            speaking_level=skill_signal_to_cefr_level(signals.speaking),
            listening_level=skill_signal_to_cefr_level(signals.listening),
            strengths_summary="strong vocabulary",
            weaknesses_summary="limited verb tenses",
        )
        assert result.reading_level is CEFRLevel.B1
        assert result.writing_level is CEFRLevel.B1
        assert result.speaking_level is CEFRLevel.A2
        assert result.listening_level is CEFRLevel.A2
        assert result.placement_session_id == session.id

    def test_no_audio_modality_leaves_speaking_and_listening_none(self) -> None:
        session = self._completed_session()
        # Text-only placement (FR-3): assessment agent never populates
        # speaking/listening signals.
        signals = SkillSignals(
            reading=SkillSignal(cefr_level="A2", confidence=0.7),
            writing=SkillSignal(cefr_level="A2", confidence=0.7),
            speaking=None,
            listening=None,
        )
        result = PlacementResult.from_completed_session(
            session,
            reading_level=skill_signal_to_cefr_level(signals.reading),
            writing_level=skill_signal_to_cefr_level(signals.writing),
            speaking_level=skill_signal_to_cefr_level(signals.speaking),
            listening_level=skill_signal_to_cefr_level(signals.listening),
            strengths_summary="x",
            weaknesses_summary="y",
        )
        assert result.speaking_level is None
        assert result.listening_level is None

    def test_raises_when_session_not_completed(self) -> None:
        in_progress_session = PlacementSession.start(uuid.uuid4(), PlacementModality.TEXT_ONLY)
        with pytest.raises(PlacementSessionNotCompletedError):
            PlacementResult.from_completed_session(
                in_progress_session,
                reading_level=CEFRLevel.A1,
                writing_level=CEFRLevel.A1,
                speaking_level=None,
                listening_level=None,
                strengths_summary="x",
                weaknesses_summary="y",
            )

    def test_generated_at_is_stamped_now(self) -> None:
        session = self._completed_session()
        before = datetime.now(UTC)
        result = PlacementResult.from_completed_session(
            session,
            reading_level=CEFRLevel.A1,
            writing_level=CEFRLevel.A1,
            speaking_level=None,
            listening_level=None,
            strengths_summary="x",
            weaknesses_summary="y",
        )
        after = datetime.now(UTC)
        assert before <= result.generated_at <= after

    def test_result_immutable_has_no_public_mutators(self) -> None:
        # Deliberate structural check: PlacementResult exposes no setter
        # methods (data-model.md: "Immutable once created").
        public_callables = [
            name
            for name in dir(PlacementResult)
            if not name.startswith("_") and callable(getattr(PlacementResult, name))
        ]
        assert public_callables == ["from_completed_session"]
