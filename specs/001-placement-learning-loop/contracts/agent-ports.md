# Agent Port Contracts: Placement & Learning Loop

Internal contracts (Constitution §5: "each agent MUST have explicit inputs, explicit outputs"). These are Python `Protocol` interfaces in `backend/src/ai_agents/ports/`, implemented by provider-specific adapters (`AnthropicAdapter`, `OpenAIAdapter`, `LocalModelAdapter` — research.md §1) and consumed only by each bounded context's application layer, never called directly from `api/` or `infrastructure/`.

Every call through any port is wrapped once, centrally, to write one `AgentInvocationLog` row (agent_name, provider, input/output summary, latency, success) — individual adapters do not implement logging themselves (NFR-4, single responsibility).

---

## `AssessmentAgentPort`

Used by the `placement` module during a `PlacementSession`.

**Input** (`AssessmentTurnInput`):
```python
{
  "conversation_so_far": list[{"sender": "student" | "agent", "text": str}],
  "latest_student_response": str,
  "audio_transcript": str | None,  # already transcribed by SpeechToTextProvider if audio modality
}
```

**Output** (`AssessmentTurnOutput`):
```python
{
  "next_prompt_text": str | None,       # None signals placement is complete
  "is_complete": bool,
  "skill_signals": {                     # only populated once is_complete=True
    "reading": {"cefr_level": str, "confidence": float} | None,
    "writing": {"cefr_level": str, "confidence": float} | None,
    "speaking": {"cefr_level": str, "confidence": float} | None,   # None if no audio modality
    "listening": {"cefr_level": str, "confidence": float} | None,  # None if no audio modality
  },
  "strengths_summary": str | None,
  "weaknesses_summary": str | None,
}
```

**Contract rule**: `skill_signals` are *inputs* to `PlacementResult` creation, not the final decision — the `placement` application service persists them verbatim into `PlacementResult` (this is the one agent whose signal *is* directly the placement outcome, since there is no prior state to reconcile against, unlike Progression below).

---

## `ConversationAgentPort`

Used by the `conversation` module for the ongoing learning-loop conversation.

**Input** (`ConversationTurnInput`):
```python
{
  "conversation_history": list[{"sender": "student" | "agent", "text": str}],
  "student_message": str,
  "audio_transcript": str | None,
  "learner_context": {                   # read-only snapshot, never mutated by the agent
    "skills": [{"skill": str, "cefr_level": str, "mastery_score": int}],
  },
}
```

**Output** (`ConversationTurnOutput`):
```python
{
  "reply_text": str,
  "scored": bool,                        # whether this turn should produce a LearningEvent
  "skill": str | None,                   # which skill this turn evaluated, if scored=True
  "performance_score": float | None,     # 0..1, only if scored=True
  "feedback_text": str | None,           # pedagogical feedback (FR-8), only if scored=True
}
```

**Contract rule**: the agent never decides XP, level advancement, or streak — it only emits `performance_score`/`feedback_text` as a *signal*. The `progression` and `gamification` modules consume the resulting `LearningEvent` independently (FR-9, FR-18).

---

## `ProgressionSignalAgentPort`

Used by the `progression` module only for activity types where correctness isn't purely rule-based (e.g., open-ended writing/speaking responses need an LLM judgment before the deterministic domain rule can run). Multiple-choice/exact-match exercises skip this port entirely and go straight to the deterministic rule.

**Input** (`ProgressionSignalInput`):
```python
{
  "activity_prompt": str,
  "student_response": str,
  "rubric": object,                      # from Activity.prompt_content
}
```

**Output** (`ProgressionSignalOutput`):
```python
{
  "performance_score": float,            # 0..1
  "feedback_text": str,
}
```

**Contract rule** (Constitution §1, §5 — the load-bearing one): this port's output is *only* a signal. The actual level-advancement decision is computed by the deterministic domain rule in `progression/domain/` (research.md §6 — windowed accuracy ≥ 80% over last 10), which is pure Python, has no dependency on this port, and is unit-tested without any agent/LLM involved (NFR-7, AC-4).

---

## Audio capability ports (FR-14, AC-7)

Not implemented end-to-end this iteration (research.md §2) — interfaces exist and are called by `conversation`/`placement`; the only bound adapter is `NullAudioAdapter`.

```python
class SpeechToTextProvider(Protocol):
    async def transcribe(self, audio_ref: str) -> str: ...

class TextToSpeechProvider(Protocol):
    async def synthesize(self, text: str) -> str:  # returns an audio_ref
        ...
```

`NullAudioAdapter.transcribe`/`.synthesize` return a well-typed "not available" result consumed by the caller to gracefully fall back to text-only (spec Edge Case: no mic/unsupported browser) — they do not raise unhandled exceptions.

---

## Testing contract (NFR-7)

Every adapter (`AnthropicAdapter`, `OpenAIAdapter`, `LocalModelAdapter`) is tested against the **same** contract test suite, parameterized by adapter, asserting only the shape above — proving AC-6 (swap the adapter, behavior contract holds) is a real, automated check, not a manual claim. `LocalModelAdapter` is deterministic (fixed canned outputs keyed by input hash) and is the one used in CI/unit tests by default; `AnthropicAdapter`/`OpenAIAdapter` are exercised only in an explicitly-tagged integration suite against recorded cassettes.
