# Phase 0 Research: Placement & Learning Loop

**Input**: `spec.md` §"Perguntas em aberto para o Technical Plan" + Technical Context unknowns from `plan.md`.

Each item below resolves one `NEEDS CLARIFICATION` from the Technical Context, or one open question the spec explicitly deferred to this plan.

---

## 1. LLM provider for the AI agents

**Decision**: Anthropic Claude (Messages API, tool/function-calling enabled) as the default `AgentPort` adapter for the Assessment/Leveling Agent, Conversation Agent, and the LLM-signal-producing portion of the Progression Agent. An `OpenAIAdapter` is implemented as a second concrete adapter (not just a stub) specifically to exercise AC-6 (provider substitutability) in integration tests. A `LocalModelAdapter` (deterministic canned/rule-based responses) backs local dev and CI when no external key is configured, per NFR-1's "fallback local/mock para dev".

**Rationale**: Claude's structured tool-calling maps cleanly onto the agents' explicit input/output contracts (Constitution §5 — "explicit inputs, explicit outputs"), the Python SDK integrates natively with FastAPI/Pydantic, and having a second real adapter (OpenAI) from day one is the cheapest way to *prove* AC-6 rather than assert it. All three adapters implement the same `AgentPort` Protocol per agent, isolated from domain code (Constitution §5, §6).

**Alternatives considered**:
- Single-provider only (Claude) — rejected: AC-6 requires proven substitutability, not just an abstraction that's never exercised.
- Open-source local LLM (e.g., Llama via Ollama) as the *primary* adapter — rejected for MVP: heavier local ops burden than justified yet; kept as a future adapter option, not blocking this slice.

---

## 2. STT/TTS provider

**Decision**: No concrete STT/TTS adapter is selected in this plan. `SpeechToTextProvider` and `TextToSpeechProvider` interfaces are defined and wired into the Conversation module per FR-14/AC-7, backed only by a `NullAudioAdapter` that raises a clear "not enabled in this release" domain-level result (not an exception that breaks the flow) when invoked. Concrete provider selection (e.g., Whisper, ElevenLabs) is explicitly deferred to the future slice that activates audio end-to-end.

**Rationale**: The spec itself scopes real STT/TTS wiring out of this iteration (FR-14: "mesmo que o primeiro release entregue apenas texto"); picking a concrete vendor now would be a premature decision with no consumer to validate it against, contradicting Constitution §17 (avoid optimization/decisions before validated demand). The interface existing and being called is what AC-7 requires — not a working implementation.

**Alternatives considered**:
- Pick Whisper (STT) + ElevenLabs (TTS) now — rejected: no acceptance criterion in this slice exercises them; premature vendor commitment.

---

## 3. REST vs GraphQL for the public API

**Decision**: REST, generated from FastAPI's native OpenAPI support.

**Rationale**: The API surface for this slice (auth, placement, conversation, exercises, progression/gamification reads) is action- and resource-oriented, not a deeply nested graph with heterogeneous client query shapes — the case where GraphQL earns its complexity. FastAPI's automatic OpenAPI schema gives a versionable, explicit contract (Constitution §14) with no extra tooling, and REST is simpler to cache, log, and secure per-endpoint (NFR-4, NFR-6). GraphQL is not ruled out permanently — it can be reconsidered if a future client (e.g., mobile) needs flexible field selection across many resources.

**Alternatives considered**:
- GraphQL — rejected for now: added schema/tooling complexity (Constitution §6 "avoid overengineering") not justified by current client needs (single web client, FR/NFR set is CRUD+action shaped).

---

## 4. Level scale: CEFR vs internal

**Decision**: Display CEFR levels (A1–C2) to the student per skill (reading/writing/speaking/listening), since it's the vocabulary students and language-learning market already understand (supports SC-001, SC-003 explainability). Internally, each skill also tracks a continuous **mastery score (0–100)** within the current CEFR level, computed from the windowed accuracy rule (see §6 below). CEFR level advances only when the windowed-accuracy rule triggers; the mastery score gives finer-grained input for activity sequencing (FR-7) and XP calculation (FR-15) without requiring a new externally-facing scale.

**Rationale**: A pure internal numeric scale would fail SC-001/SC-003 (student-facing explainability) since CEFR is the domain-standard vocabulary. A pure CEFR-only scale (6 buckets) is too coarse to drive gamified per-activity XP variation or fine-grained activity sequencing. Combining both satisfies both needs without inventing a second externally-visible scale.

**Alternatives considered**:
- CEFR-only, no internal sub-scale — rejected: too coarse for XP/activity sequencing granularity.
- Fully custom internal scale (no CEFR) — rejected: fails student-facing explainability (SC-001, SC-003) and industry familiarity.

---

## 5. Cache / session strategy (Redis)

**Decision**: No Redis (or other cache/session store) in this iteration. Session/auth state (refresh tokens) is stored in PostgreSQL; no additional caching layer is introduced.

**Rationale**: Constitution §17 (MVP: avoid distributed systems/extra infra unless demand justifies) and §6 (avoid premature optimization). Nothing in this slice's NFRs (in particular NFR-5's ~3s conversation-turn budget) requires a cache to be met — the budget is dominated by the LLM call itself, not by data access. Docker Compose keeps an *optional* commented-out Redis service placeholder for when a future slice (e.g., real-time features, rate limiting at scale) justifies it, but it is not started by default.

**Alternatives considered**:
- Redis for session storage now — rejected: no measured need yet; adds an operational dependency to the local-first stack (NFR-1) without a justified requirement.

---

## 6. Level-advancement rule: accuracy threshold & window size

**Decision**: A skill's CEFR level advances when the student's accuracy rate is **≥ 80%** across the **last 10 scored activities** in that skill (window slides per new activity; fewer than 10 activities recorded yet uses all activities available so far, i.e., no advancement is possible before at least 5 activities exist, to avoid one lucky answer triggering a level-up). A single incorrect answer inside an otherwise-strong window does not reset progress (per the spec's Clarifications). Below-threshold performance never regresses the level (per spec FR-9); it instead biases the next-activity selection (FR-7) toward reinforcement content in the same level/skill.

**Rationale**: 80%/10 is a common, easily-explainable threshold in adaptive-learning literature (roughly "4 out of 5 sustained"), keeps the rule simple enough to unit-test deterministically (NFR-7, Constitution §11) with a fixed-size sliding window, and the 5-activity minimum avoids statistically meaningless early triggers. This is a starting calibration, expected to be tuned from real usage data post-launch — it is intentionally implemented as a named constant in the Progression module, not hardcoded inline, so it can be tuned without a domain rewrite.

**Alternatives considered**:
- Streak-based ("N correct in a row") — rejected in Clarifications: one mistake would unfairly reset an otherwise strong track record.
- Fixed activity count regardless of accuracy — rejected: decouples advancement from actual mastery, contradicting FR-9's "auditável" and pedagogically meaningful decision requirement.

---

## 7. XP formula

**Decision**: `xp_awarded = base_xp(activity_type) * max(0.25, performance_score)`, rounded to the nearest integer, where `performance_score` is the 0.0–1.0 score already produced by the relevant agent for that activity (the same signal FR-9 consumes for progression), and `base_xp(activity_type)` is a fixed table: conversation turn = 5, writing exercise = 10, speaking exercise = 10, listening exercise = 8 (speaking/writing weighted higher as they are typically more effortful/slower to produce). The `0.25` floor guarantees participation always earns some XP (keeps the gamified loop encouraging per FR-18's "reforço motivacional" intent) even on a wrong answer, consistent with FR-9's "never punish, reinforce instead" policy.

**Rationale**: Reuses the same performance signal already computed for progression (Constitution §12 — one event, one source of truth, no parallel/contradictory scoring pipeline), keeps the formula simple enough to unit-test deterministically, and the participation floor avoids XP feeling punitive, which would work against the moderate-gamification goal from Clarifications (encouragement, not punishment).

**Alternatives considered**:
- Binary XP (full XP or zero) — rejected: contradicts the "reinforcement, not punishment" policy established in Clarifications/FR-9.
- XP independent of performance (flat per activity) — rejected: removes the feedback signal that ties gamification to genuine progress (FR-18 requires XP to be "influenced by" performance, not decoupled from it).

---

## 8. Module / bounded context structure inside the monolith

**Decision**: Six backend modules, each internally layered per Clean Architecture (`domain/ application/ infrastructure/ api/`):

1. `identity` — accounts, auth, credentials.
2. `placement` — `PlacementSession`, `PlacementResult`, the placement conversation flow.
3. `conversation` — `ConversationSession`, `Message`, the post-placement conversation loop.
4. `progression` — `LearnerProfile` projection, the level-advancement domain rule (§6 above), activity sequencing.
5. `gamification` — `GamificationProfile`, `Badge`, XP/streak rules (§7 above); reads the same `LearningEvent` stream as `progression` but is a separate bounded context so motivational mechanics never leak into (or gate) the pedagogical progression rule (FR-18).
6. `ai_agents` — `AgentPort` interfaces per agent, provider adapters (§1), `SpeechToTextProvider`/`TextToSpeechProvider` interfaces (§2), `AgentInvocationLog`.

Plus a `shared_kernel` for cross-module primitives (base entity/value-object types, the domain event bus used to publish `LearningEvent`) and `learning_content` for `LearningPath`/`Unit`/`Activity` (shared read model consumed by both `conversation` and `progression`).

**Rationale**: 1:1 mapping to the bounded contexts already named in spec.md's Technology Choices table, keeping `progression` (pedagogical decision, auditable) and `gamification` (motivational reinforcement) as separate contexts is what makes FR-18's "does not replace the domain rule" constraint structurally enforced rather than just documented. Dependencies still point inward per module (Constitution §3); cross-module communication happens only through published `LearningEvent`s or explicit application-layer interfaces, never direct domain reach-through.

**Alternatives considered**:
- Merge `gamification` into `progression` — rejected: would blur the "XP/streak never substitutes the progression rule" boundary (FR-18) into a single module where that discipline is easy to erode over time.

---

## 9. Testing tooling

**Decision**: Backend — `pytest` + `pytest-asyncio` + FastAPI's `TestClient`/`httpx` for API-level integration tests; `vcrpy`-style recorded cassettes (or hand-authored fixture payloads for pure-unit agent tests) for anything touching an `AgentPort` adapter, satisfying NFR-7's "mockadas/gravadas" requirement. Frontend — `Vitest` + `React Testing Library` for component/unit tests, `Playwright` for the E2E journeys in spec.md's Testing Strategy (against the full `docker compose up` stack, satisfying AC-5/AC-8).

**Rationale**: All are the de-facto standard, actively maintained choices for a FastAPI + Next.js stack; no exotic tooling, consistent with Constitution §6 (mature ecosystems, avoid unnecessary frameworks).

**Alternatives considered**: None seriously considered — these are uncontested defaults for this stack; not worth spending scope-3 clarification budget on.

---

## 10. Auth mechanism

**Decision**: Email/password (FR-1) hashed with `bcrypt` (via `passlib`), issuing a short-lived JWT access token (~15 min) plus a longer-lived refresh token (~30 days) stored server-side in PostgreSQL (hashed, revocable). The web client (Next.js) proxies auth through its own backend-for-frontend route so the token never touches client-side JS storage (httpOnly cookie); the underlying API also accepts a standard `Authorization: Bearer` header so a future mobile client (NFR-8) can authenticate identically without any backend contract change.

**Rationale**: Satisfies FR-1's "OAuth-ready without breaking contracts" (JWT issuance is orthogonal to credential source — adding an OAuth flow later just adds another way to obtain the same token), and NFR-8's client-agnostic requirement, while keeping the web client secure against XSS token theft.

**Alternatives considered**:
- Server-side session cookie only (no bearer token support) — rejected: breaks NFR-8's mobile-reuse requirement without a rework.

---

## Summary of resolved unknowns

| Technical Context field | Resolution |
|---|---|
| Language/Version | TypeScript 5.x (Next.js) frontend; Python 3.12 (FastAPI) backend |
| Primary Dependencies | Next.js/React, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, `anthropic` SDK, `openai` SDK (2nd adapter) |
| Storage | PostgreSQL 16 (+ pgvector) |
| Testing | pytest/pytest-asyncio/httpx + vcrpy-style cassettes (backend); Vitest/RTL + Playwright (frontend) |
| Target Platform | Docker Compose (Linux containers) for backend/db; any evergreen browser for frontend |
| Project Type | Web application (frontend + backend) |
| Performance Goals | Conversation turn ≤ ~3s (NFR-5) |
| Constraints | Local-first (NFR-1), no proprietary cloud lock-in (NFR-2), env-var config (NFR-3), structured agent-call logging (NFR-4), auth+TLS (NFR-6) |
| Scale/Scope | MVP/local-first, single-instance; no explicit concurrency target this iteration (deferred to the future cloud-deploy spec, per spec.md Assumptions) |
