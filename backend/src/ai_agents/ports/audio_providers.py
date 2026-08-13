"""Port contracts for the audio capability providers (FR-14, AC-7).

Not implemented end-to-end this iteration (research.md §2) — interfaces
exist and are called by ``conversation``/``placement``; the only bound
adapter this iteration is ``NullAudioAdapter``.

**Deviation from the literal contracts/agent-ports.md snippet**: that doc
shows ``transcribe``/``synthesize`` returning a plain ``str``. That shape
cannot represent "not available" without either raising (research.md §2
explicitly rules this out: "a clear ... result, not an exception that
breaks the flow") or returning a magic string, which is fragile for
callers to check correctly. Both Protocols here are widened to return
``AudioProviderResult`` instead of ``str`` — a small typed result object
with ``available: bool`` and ``value: str | None`` — so callers can do
``if not result.available: fall back to text-only`` without relying on
string-sniffing. This is a deliberate, documented deviation; a follow-up
note is owed on contracts/agent-ports.md to reflect the widened return
type for both Protocols.

For ``SpeechToTextProvider.transcribe``, ``value`` (when available) is the
transcribed text. For ``TextToSpeechProvider.synthesize``, ``value`` (when
available) is an ``audio_ref`` pointing at the synthesized audio.
"""

from typing import Protocol

from pydantic import BaseModel


class AudioProviderResult(BaseModel):
    """Typed result of an audio-provider call, in place of a raw ``str``.

    ``available=False`` means the provider could not (or does not) fulfill
    the request — callers must check this and gracefully fall back to
    text-only (spec Edge Case: no mic/unsupported browser) rather than
    treat a missing/None value as an error to propagate.
    """

    available: bool
    value: str | None = None


class SpeechToTextProvider(Protocol):
    """Structural interface implemented by every speech-to-text adapter."""

    async def transcribe(self, audio_ref: str) -> AudioProviderResult:
        """Transcribe the audio at ``audio_ref`` into text, if available."""
        ...


class TextToSpeechProvider(Protocol):
    """Structural interface implemented by every text-to-speech adapter."""

    async def synthesize(self, text: str) -> AudioProviderResult:
        """Synthesize ``text`` into audio, returning an audio_ref if available."""
        ...
