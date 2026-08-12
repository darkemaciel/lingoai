# Quickstart: Validating the Placement & Learning Loop

Proves the acceptance criteria in `spec.md` end-to-end, locally, per NFR-1/AC-5.

## Prerequisites

- Docker + Docker Compose
- An API key for at least one LLM provider (Anthropic or OpenAI) in `.env` — see `.env.example` — **or** leave unset to run against `LocalModelAdapter` (deterministic mock), which is sufficient for every scenario below except the "swap provider" one.

## Setup

```bash
cp .env.example .env        # fill AI provider key, or leave AI_PROVIDER=local
docker compose up --build
docker compose exec backend alembic upgrade head
```

Expected: `frontend` reachable at `http://localhost:3000`, `backend` health check `GET /api/v1/health` returns `200`, no service depends on anything outside these containers except the outbound call to the configured AI provider (or none, if `AI_PROVIDER=local`).

## Scenario 1 — Placement (AC-1)

1. Open `http://localhost:3000`, register a new account (email/password).
2. Placement starts automatically (FR-2). Answer the guided text conversation.
3. On completion, the result screen shows a CEFR level per skill plus strengths/weaknesses (FR-5).

**Verify**: `GET /api/v1/placement/sessions/{id}/result` returns a populated `PlacementResult`; `GET /api/v1/progression/profile` shows one `LearnerSkillProfile` row per skill seeded from that result.

## Scenario 2 — Learning loop + feedback (AC-2, AC-3)

1. After placement, accept the first recommended activity (`GET /api/v1/activities/next`).
2. Submit an answer, including at least one deliberately wrong answer.

**Verify**:
- Response includes `feedback_text` explaining the error, not just a correctness flag (AC-3).
- A new row exists in `LearningEvent` for this submission.
- Submitting the exact same `client_submission_id` twice does not create a second `LearningEvent` or double-count XP (idempotency, spec Edge Case).

## Scenario 3 — Gamified progression feedback (Clarifications session)

1. Complete 5+ activities in the same skill, mixing correct and incorrect answers, keeping accuracy ≥ 80%.

**Verify**:
- Each activity response includes an inline `gamification_delta` (XP gained, streak, any badge) in the same API response as the activity result (FR-19, SC-007) — no extra round trip needed.
- `GET /api/v1/gamification/profile` shows the same XP/streak/badges, confirming the persistent panel matches the inline feedback.
- Once the accuracy-window rule is satisfied (research.md §6), the skill's `cefr_level` in `GET /api/v1/progression/profile` advances, and a `level_advanced` `LearningEvent` is recorded.

## Scenario 4 — Progression never regresses (spec Clarifications)

1. For a skill already at a given `cefr_level`, submit several consecutive wrong answers (accuracy well below 80%).

**Verify**: `cefr_level` for that skill is unchanged in `GET /api/v1/progression/profile` — only `mastery_score` and the next recommended activity's difficulty shift toward reinforcement (FR-7, FR-9). No API response ever reports a level decrease.

## Scenario 5 — Auditable progression (AC-4)

1. Pick any student with at least one level advancement.
2. Call `GET /api/v1/progression/profile/{skill}/history`.

**Verify**: the returned `LearningEvent` sequence, replayed through the documented rule (research.md §6: ≥80% over the last 10 scored events), deterministically reproduces the current `cefr_level` — the justification is data + a documented rule, not an LLM explanation.

## Scenario 6 — AI provider substitutability (AC-6)

1. With the stack running against `AI_PROVIDER=anthropic` (or `local`), complete one conversation turn and note the reply style.
2. Stop the backend, change `.env` to `AI_PROVIDER=openai` (or back to `local`), restart only the `backend` service (`docker compose restart backend`) — no code change, no rebuild.
3. Complete another conversation turn.

**Verify**: the API contract (`POST /api/v1/conversations/{id}/messages` response shape) is identical in both runs; no domain code changed; `AgentInvocationLog.provider` reflects the swap.

## Scenario 7 — Audio interface exists but isn't wired (AC-7)

**Verify** (code-level, not UI): `conversation` and `placement` application services import and call `SpeechToTextProvider`/`TextToSpeechProvider` from `ai_agents/ports`; the bound implementation is `NullAudioAdapter`, which returns a typed "unavailable" result rather than raising — confirm by unit test, not manual UI check (there is no audio UI yet this iteration).

## Scenario 8 — Deterministic test suite (AC-8)

```bash
docker compose exec backend pytest
```

**Verify**: full suite passes with `AI_PROVIDER=local` (no network calls); progression-rule unit tests (research.md §6) and placement-derivation unit tests run with zero external dependencies; adapter contract tests (contracts/agent-ports.md "Testing contract") run against recorded cassettes only, never live APIs, in this default run.
