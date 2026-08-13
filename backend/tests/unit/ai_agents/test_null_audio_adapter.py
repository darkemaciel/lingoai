"""Unit test (T065): `NullAudioAdapter` returns a typed "unavailable"
result (never raises) and is actually wired into the `placement`/
`conversation` application services (AC-7) — even though no real STT/TTS
vendor is bound this iteration (research.md §2).
"""

from __future__ import annotations

import pytest

from ai_agents.adapters.null_audio_adapter import NullAudioAdapter
from ai_agents.ports.audio_providers import AudioProviderResult


@pytest.fixture
def adapter() -> NullAudioAdapter:
    return NullAudioAdapter()


class TestNullAudioAdapter:
    async def test_transcribe_reports_not_available(self, adapter: NullAudioAdapter) -> None:
        result = await adapter.transcribe("audio://some-ref")
        assert isinstance(result, AudioProviderResult)
        assert result.available is False
        assert result.value is None

    async def test_synthesize_reports_not_available(self, adapter: NullAudioAdapter) -> None:
        result = await adapter.synthesize("Hello, how are you?")
        assert isinstance(result, AudioProviderResult)
        assert result.available is False
        assert result.value is None

    async def test_never_raises_regardless_of_input(self, adapter: NullAudioAdapter) -> None:
        # Empty string, unusual refs — a well-typed "not available" result
        # every time, never an exception (spec Edge Case: no mic/unsupported
        # browser must degrade gracefully, not error out).
        for value in ("", "not-a-real-ref", "🎤"):
            transcribe_result = await adapter.transcribe(value)
            synthesize_result = await adapter.synthesize(value)
            assert transcribe_result.available is False
            assert synthesize_result.available is False


class TestAudioPortsWiredIntoApplicationServices:
    """AC-7: confirm the audio interfaces are invoked by the conversation/
    placement layers, even though nothing is bound end-to-end yet. Full
    call-path exercise (an actual `audio_ref` round trip through
    `submit_answer`/`send_message`) requires a live DB — covered
    structurally there; this confirms the wiring point itself without one.
    """

    def test_placement_service_holds_a_null_audio_adapter(self) -> None:
        from placement.application import placement_service

        assert isinstance(placement_service._audio_adapter, NullAudioAdapter)

    def test_conversation_service_holds_a_null_audio_adapter(self) -> None:
        from conversation.application import conversation_service

        assert isinstance(conversation_service._audio_adapter, NullAudioAdapter)
