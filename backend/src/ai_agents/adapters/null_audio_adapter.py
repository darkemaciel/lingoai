"""Null-object implementation of the audio capability ports (FR-14, AC-7).

Per research.md §2: no concrete STT/TTS adapter is selected in this plan.
``NullAudioAdapter`` exists so ``placement``/``conversation`` application
services can call ``SpeechToTextProvider``/``TextToSpeechProvider`` today
(proving the interfaces are wired end-to-end, AC-7) even though no real
vendor is bound yet.

**Never raises.** Both methods always return
``AudioProviderResult(available=False, value=None)`` — a well-typed "not
available" result, never an exception. This lets a caller gracefully fall
back to text-only (spec Edge Case: no mic/unsupported browser) with a
simple ``if not result.available:`` check, rather than needing a
try/except around every audio call.

See ``ai_agents/ports/audio_providers.py`` for why the Protocols return
``AudioProviderResult`` rather than a plain ``str`` (a deliberate widening
of the literal shape shown in contracts/agent-ports.md).
"""

from ai_agents.ports.audio_providers import AudioProviderResult


class NullAudioAdapter:
    """Implements both `SpeechToTextProvider` and `TextToSpeechProvider`.

    Always reports "not available" rather than raising, since no concrete
    STT/TTS vendor is bound in this iteration.
    """

    async def transcribe(self, audio_ref: str) -> AudioProviderResult:
        """Always returns "not available" — no STT provider is bound."""
        return AudioProviderResult(available=False, value=None)

    async def synthesize(self, text: str) -> AudioProviderResult:
        """Always returns "not available" — no TTS provider is bound."""
        return AudioProviderResult(available=False, value=None)
