---

description: "Task list for Placement & Learning Loop"
---

# Tasks: Placement & Learning Loop

**Input**: Design documents from `/specs/001-placement-learning-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/rest-api.md, contracts/agent-ports.md, quickstart.md

**Tests**: Included — spec.md's Testing Strategy and NFR-7 explicitly require deterministic automated tests (unit for domain rules, integration for API→domain→DB flows, contract tests for agent adapters, E2E for critical journeys), so test tasks are part of every story phase, not optional here.

**Organization**: Tasks are grouped by user story (US1 = Nivelamento, P1; US2 = Loop de aprendizagem, P2; US3 = Plataforma extensível, P3) per spec.md, to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths follow plan.md's Project Structure (`backend/src/<module>/{domain,application,infrastructure,api}/`, `frontend/src/`)

## Path Conventions

Web application per plan.md: `backend/src/`, `backend/tests/`, `backend/migrations/`, `frontend/src/`, `frontend/tests/`, `docker-compose.yml` at repo root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create backend project skeleton per plan.md Project Structure: `backend/src/{identity,placement,conversation,progression,gamification,learning_content,ai_agents,shared_kernel}/{domain,application,infrastructure,api}/__init__.py`, `backend/src/app.py`, `pyproject.toml` (FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, `anthropic`, `openai`, `passlib[bcrypt]`, `python-jose`)
- [ ] T002 [P] Create frontend project skeleton: `frontend/` Next.js 14+ app (TypeScript, app router) with `frontend/src/{app,components,services}/`
- [ ] T003 [P] Configure backend linting/formatting (`ruff`, `black`, `mypy` config in `pyproject.toml`) and frontend linting/formatting (`eslint`, `prettier` config in `frontend/.eslintrc.json`, `frontend/.prettierrc`)
- [ ] T004 [P] `docker-compose.yml` (frontend, backend, postgres services; Redis placeholder commented out per research.md §5) and `.env.example` (DB creds, `AI_PROVIDER`, provider API keys, JWT secret)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Configure Alembic (`backend/migrations/env.py`, `backend/alembic.ini`) wired to SQLAlchemy 2.x declarative base and DB session/engine setup in `backend/src/shared_kernel/infrastructure/db.py`
- [ ] T006 [P] `shared_kernel` base entity/value-object types and the domain event bus (publishes `LearningEvent`) in `backend/src/shared_kernel/domain/base.py`, `backend/src/shared_kernel/domain/event_bus.py`
- [ ] T007 [P] `User` SQLAlchemy model + Alembic migration in `backend/src/identity/infrastructure/models.py` (email unique, `password_hash`, `native_language`, `timezone`, `created_at` per data-model.md)
- [ ] T008 [P] `LearningEvent` SQLAlchemy model + Alembic migration (append-only; unique constraint on `user_id`+`client_submission_id`) in `backend/src/shared_kernel/infrastructure/learning_event_model.py`
- [ ] T009 [P] `AgentInvocationLog` SQLAlchemy model + Alembic migration, plus the centralized logging wrapper that every `AgentPort` call goes through (NFR-4) in `backend/src/ai_agents/observability/agent_invocation_log.py`
- [ ] T010 identity: bcrypt password hashing + JWT access/refresh token issuance and validation utilities in `backend/src/identity/infrastructure/security.py` (depends on T007)
- [ ] T011 identity: register/login/refresh application use cases in `backend/src/identity/application/auth_service.py` (depends on T010)
- [ ] T012 identity: `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh` routes in `backend/src/identity/api/routes.py` (depends on T011)
- [ ] T013 [P] `ai_agents` port Protocol definitions — `AssessmentAgentPort`, `ConversationAgentPort`, `ProgressionSignalAgentPort`, `SpeechToTextProvider`, `TextToSpeechProvider` — per contracts/agent-ports.md, in `backend/src/ai_agents/ports/*.py`
- [ ] T014 [P] `LocalModelAdapter` deterministic implementation of all three agent ports (canned/rule-based outputs keyed by input hash) in `backend/src/ai_agents/adapters/local_model_adapter.py` (depends on T013)
- [ ] T015 [P] `NullAudioAdapter` implementation of `SpeechToTextProvider`/`TextToSpeechProvider` returning a typed "not available" result in `backend/src/ai_agents/adapters/null_audio_adapter.py` (depends on T013)
- [ ] T016 FastAPI app assembly, DI wiring, error-handling middleware (shared `{"error": {"code","message"}}` shape), `GET /api/v1/health` in `backend/src/app.py` (depends on T012, T014, T015)
- [ ] T017 [P] Frontend app shell/routing skeleton, typed API client base, BFF auth route storing tokens in an httpOnly cookie per research.md §10, in `frontend/src/app/api/auth/route.ts`, `frontend/src/services/api-client.ts`
- [ ] T018 [P] Backend test scaffolding: `pytest`/`pytest-asyncio` config, DB test fixtures, `TestClient`/`httpx` fixture, `LocalModelAdapter` fixture in `backend/tests/conftest.py`; frontend test scaffolding: Vitest+RTL config in `frontend/vitest.config.ts`, Playwright config in `frontend/playwright.config.ts`

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Nivelamento inicial do estudante (Priority: P1) 🎯 MVP

**Goal**: A new student registers, is automatically guided through a text-based AI placement conversation, and receives a persisted per-skill CEFR `PlacementResult`.

**Independent Test**: Register a new account, complete the placement conversation in text, verify a per-skill level result is generated and displayed — no dependency on the rest of the learning loop.

### Tests for User Story 1

- [ ] T019 [P] [US1] Unit test: `PlacementResult` derivation from `AssessmentAgentPort` output (skill_signals → persisted levels) in `backend/tests/unit/placement/test_placement_result_derivation.py`
- [ ] T020 [P] [US1] Contract test: `AssessmentAgentPort` via `LocalModelAdapter` matches the input/output shape in contracts/agent-ports.md, in `backend/tests/unit/ai_agents/test_assessment_agent_port_contract.py`
- [ ] T021 [P] [US1] Integration test: `POST /placement/sessions` → `POST /placement/sessions/{id}/answers` (loop to completion) → `GET /placement/sessions/{id}/result` in `backend/tests/integration/test_placement_flow.py`
- [ ] T022 [P] [US1] E2E test: register → placement conversation → result summary screen in `frontend/tests/e2e/placement.spec.ts`

### Implementation for User Story 1

- [ ] T023 [P] [US1] `PlacementSession` domain entity + state transitions (`in_progress → completed`/`abandoned`) in `backend/src/placement/domain/placement_session.py`
- [ ] T024 [P] [US1] `PlacementResult` domain entity + validation (only creatable when session completed; immutable) in `backend/src/placement/domain/placement_result.py`
- [ ] T025 [P] [US1] `LearnerSkillProfile` SQLAlchemy model + Alembic migration (unique on `user_id`+`skill`) in `backend/src/progression/infrastructure/models.py`
- [ ] T026 [P] [US1] `GamificationProfile` SQLAlchemy model + Alembic migration (unique on `user_id`) in `backend/src/gamification/infrastructure/models.py`
- [ ] T027 [US1] `PlacementSession`/`PlacementResult` SQLAlchemy models + Alembic migration in `backend/src/placement/infrastructure/models.py` (depends on T023, T024)
- [ ] T028 [US1] Placement application service — `start_session`, `submit_answer` (calls `AssessmentAgentPort`), `complete_session` — in `backend/src/placement/application/placement_service.py` (depends on T014, T023, T024, T027)
- [ ] T029 [US1] Placement application service: on completion, bootstrap one `LearnerSkillProfile` row per non-null skill level and one `GamificationProfile` row (idempotent, one-time) in `backend/src/placement/application/placement_service.py` (depends on T025, T026, T028)
- [ ] T030 [US1] Placement API routes — `POST /api/v1/placement/sessions`, `POST /api/v1/placement/sessions/{id}/answers`, `GET /api/v1/placement/sessions/{id}/result` — in `backend/src/placement/api/routes.py` (depends on T028, T029)
- [ ] T031 [US1] Progression read route `GET /api/v1/progression/profile` (seeded rows only at this stage) in `backend/src/progression/api/routes.py` (depends on T025)
- [ ] T032 [P] [US1] Frontend: registration page that auto-starts placement on first login (FR-2) in `frontend/src/app/(auth)/register/page.tsx`
- [ ] T033 [P] [US1] Frontend: placement conversation UI (text input/output loop) in `frontend/src/app/placement/page.tsx`
- [ ] T034 [US1] Frontend: placement result summary screen (level per skill, strengths/weaknesses) in `frontend/src/app/placement/result/page.tsx` (depends on T033)

**Checkpoint**: User Story 1 is fully functional and independently testable (AC-1, SC-001)

---

## Phase 4: User Story 2 - Loop de aprendizagem com feedback e progressão (Priority: P2)

**Goal**: After placement, the student gets a continuous loop of conversation + exercises, each answer yielding pedagogical feedback and an immutable `LearningEvent`, driving a deterministic, auditable level-advancement rule and inline gamification (XP/streak/badges).

**Independent Test**: With a pre-existing placed student, complete one activity (conversation turn or exercise) and verify: (a) the activity matches the student's level, (b) feedback explains the error/success, (c) an immutable `LearningEvent` is recorded and the level decision is reconstructible from it.

### Tests for User Story 2

- [ ] T035 [P] [US2] Unit test: windowed-accuracy level-advancement rule — advances at ≥80%/last 10, never regresses, single miss doesn't reset — in `backend/tests/unit/progression/test_level_advancement_rule.py`
- [ ] T036 [P] [US2] Unit test: XP formula (`base_xp(type) * max(0.25, performance_score)`) in `backend/tests/unit/gamification/test_xp_formula.py`
- [ ] T037 [P] [US2] Unit test: streak update rule (timezone-aware day boundary, consecutive/reset/no-op cases) in `backend/tests/unit/gamification/test_streak_rule.py`
- [ ] T038 [P] [US2] Contract test: `ConversationAgentPort` and `ProgressionSignalAgentPort` via `LocalModelAdapter` in `backend/tests/unit/ai_agents/test_conversation_and_progression_ports_contract.py`
- [ ] T039 [P] [US2] Integration test: submit exercise answer → `LearningEvent` persisted → `feedback_text` + `gamification_delta` in response (AC-2, AC-3) in `backend/tests/integration/test_activity_answer_flow.py`
- [ ] T040 [P] [US2] Integration test: duplicate `client_submission_id` is idempotent, no double-counted XP/profile update in `backend/tests/integration/test_learning_event_idempotency.py`
- [ ] T041 [P] [US2] Integration test: conversation turn end-to-end (message → agent reply ≤ ~3s budget, scored turns produce `LearningEvent`) in `backend/tests/integration/test_conversation_flow.py`
- [ ] T042 [P] [US2] E2E test: post-placement loop shows inline XP/streak/badge after an activity and matches the persistent progress panel (FR-19, SC-007) in `frontend/tests/e2e/learning_loop.spec.ts`

### Implementation for User Story 2

- [ ] T043 [P] [US2] `LearningPath`/`Unit`/`Activity` SQLAlchemy models + Alembic migration + seed data script in `backend/src/learning_content/infrastructure/models.py`, `backend/src/learning_content/infrastructure/seed.py`
- [ ] T044 [P] [US2] `ConversationSession`/`Message` SQLAlchemy models + Alembic migration in `backend/src/conversation/infrastructure/models.py`
- [ ] T045 [P] [US2] `Badge`/`BadgeAward` SQLAlchemy models + Alembic migration + badge catalog seed data (`first_conversation_completed`, `streak_7_days`, `first_level_advanced`) in `backend/src/gamification/infrastructure/models.py`, `backend/src/gamification/infrastructure/seed.py`
- [ ] T046 [US2] Progression domain rule: `accuracy_window` append/trim (max 10) + `mastery_score` recompute + level-advancement decision (≥80% over ≥5 of last 10, never regresses) in `backend/src/progression/domain/level_advancement_rule.py` (depends on T025)
- [ ] T047 [US2] Gamification domain rule: XP formula per research.md §7 in `backend/src/gamification/domain/xp_rule.py` (depends on T026)
- [ ] T048 [US2] Gamification domain rule: streak update (timezone-aware, reset-without-tolerance) in `backend/src/gamification/domain/streak_rule.py` (depends on T026)
- [ ] T049 [US2] Gamification domain rule: badge milestone evaluation against `Badge` catalog in `backend/src/gamification/domain/badge_rule.py` (depends on T045)
- [ ] T050 [US2] Shared `LearningEvent` recorder application service — idempotent create on (`user_id`, `client_submission_id`) — in `backend/src/shared_kernel/application/learning_event_recorder.py` (depends on T008)
- [ ] T051 [US2] Progression application service: next-activity selection from `LearnerSkillProfile.mastery_score`/`cefr_level` in `backend/src/progression/application/activity_selection_service.py` (depends on T043, T046)
- [ ] T052 [US2] Conversation application service: send message → `ConversationAgentPort` → (if `scored`) `LearningEvent` → progression + gamification updates in `backend/src/conversation/application/conversation_service.py` (depends on T044, T050, T046, T047, T048)
- [ ] T053 [US2] Activity-answer application service: submit answer → deterministic scoring or `ProgressionSignalAgentPort` (open-ended) → `LearningEvent` → progression + gamification + badge updates → feedback response in `backend/src/learning_content/application/activity_answer_service.py` (depends on T043, T050, T046, T047, T048, T049)
- [ ] T054 [US2] Conversation API routes — `POST /api/v1/conversations`, `POST /api/v1/conversations/{id}/messages` — in `backend/src/conversation/api/routes.py` (depends on T052)
- [ ] T055 [US2] Activities API routes — `GET /api/v1/activities/next`, `POST /api/v1/activities/{id}/answers` — in `backend/src/learning_content/api/routes.py` (depends on T051, T053)
- [ ] T056 [US2] Progression API route `GET /api/v1/progression/profile/{skill}/history` in `backend/src/progression/api/routes.py` (depends on T046)
- [ ] T057 [US2] Gamification API route `GET /api/v1/gamification/profile` in `backend/src/gamification/api/routes.py` (depends on T047, T048, T049)
- [ ] T058 [P] [US2] Frontend: exercise activity UI with pedagogical feedback display in `frontend/src/app/learn/page.tsx`
- [ ] T059 [P] [US2] Frontend: post-placement conversation UI in `frontend/src/app/learn/conversation/page.tsx`
- [ ] T060 [P] [US2] Frontend: inline gamification feedback component (XP gained, streak, badges unlocked) in `frontend/src/components/GamificationFeedback.tsx`
- [ ] T061 [US2] Frontend: persistent progress panel (XP total, streak, badges) in `frontend/src/app/progress/page.tsx` (depends on T057)

**Checkpoint**: User Stories 1 AND 2 both work independently (AC-2, AC-3, AC-4, SC-002, SC-003, SC-005, SC-007)

---

## Phase 5: User Story 3 - Plataforma extensível (Priority: P3)

**Goal**: Prove the AI-provider is swappable without domain changes, agents are independently testable without a live LLM, and audio ports exist and are called without being wired end-to-end.

**Independent Test**: Swap the Conversation Agent's configured AI provider and confirm the observable API contract/behavior is unchanged; confirm audio interfaces exist and are invoked by the conversation/placement layers even though no real STT/TTS is bound yet.

### Tests for User Story 3

- [ ] T062 [P] [US3] Contract test: `AnthropicAdapter` against a recorded cassette, same contract-test suite as `LocalModelAdapter` in `backend/tests/contract/test_anthropic_adapter.py`
- [ ] T063 [P] [US3] Contract test: `OpenAIAdapter` against a recorded cassette in `backend/tests/contract/test_openai_adapter.py`
- [ ] T064 [P] [US3] Integration test: switching `AI_PROVIDER` config yields an identical `POST /conversations/{id}/messages` response contract (AC-6) in `backend/tests/integration/test_provider_swap.py`
- [ ] T065 [P] [US3] Unit test: `NullAudioAdapter` returns a typed "unavailable" result and is actually invoked by `placement`/`conversation` application services (AC-7) in `backend/tests/unit/ai_agents/test_null_audio_adapter.py`

### Implementation for User Story 3

- [ ] T066 [P] [US3] `AnthropicAdapter` implementing all three agent ports in `backend/src/ai_agents/adapters/anthropic_adapter.py`
- [ ] T067 [P] [US3] `OpenAIAdapter` implementing all three agent ports in `backend/src/ai_agents/adapters/openai_adapter.py`
- [ ] T068 [US3] `AI_PROVIDER`-driven adapter selection/DI wiring (env-var config, NFR-3) in `backend/src/ai_agents/adapter_factory.py` (depends on T066, T067)
- [ ] T069 [US3] Wire `SpeechToTextProvider`/`TextToSpeechProvider` calls into `placement` and `conversation` application services with graceful "not available" fallback (FR-14) in `backend/src/placement/application/placement_service.py`, `backend/src/conversation/application/conversation_service.py` (depends on T015)

**Checkpoint**: All user stories independently functional (AC-6, AC-7, SC-006)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T070 [P] Audit structured logging coverage for every agent-port call against NFR-4 (agent, input summary, latency, success/error, no raw PII) across `backend/src/ai_agents/observability/`
- [ ] T071 [P] Security hardening pass: input validation review, rate limiting on `/auth/*` endpoints, confirm no `password_hash`/raw prompts/`AgentInvocationLog` leak in any response (NFR-6, Constitution §14)
- [ ] T072 [P] Review generated OpenAPI schema for `/api/v1` against contracts/rest-api.md for drift
- [ ] T073 Run `quickstart.md` Scenarios 1–8 end-to-end via `docker compose up` (AC-5, AC-8)
- [ ] T074 [P] `README.md` with local setup instructions (`docker compose up`, `alembic upgrade head`, running tests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; consumes `LearnerSkillProfile`/`GamificationProfile` bootstrapped by US1's placement flow, so a placed student is a functional precondition for its Independent Test, but no US2 code imports US1 code directly
- **User Story 3 (Phase 5)**: Depends on Foundational's `ai_agents` port definitions (T013); exercises the same ports US1/US2 already call, so is easiest to validate once US1+US2 exist, though not code-dependent on them
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories
- **US2 (P2)**: Independently testable given a pre-placed student fixture; does not import US1 application code
- **US3 (P3)**: Independently testable by swapping adapter config; does not import US1/US2 application code

### Within Each User Story

- Tests written first, expected to fail before implementation
- Domain entities → infrastructure models/migrations → application services → API routes → frontend
- Story complete before moving to the next priority (if working sequentially)

### Parallel Opportunities

- All Setup tasks marked [P] (T002–T004) run in parallel after T001
- Foundational [P] tasks (T006, T007, T008, T009, T013, T014, T015, T017, T018) run in parallel once T005 completes
- Once Foundational completes, US1, US2, and US3 test-writing can start in parallel across contributors (US2/US3 implementation is still logically gated on US1 producing a placed-student fixture for realistic integration testing)
- Within each story, all [P] model/domain tasks run in parallel; frontend [P] tasks run in parallel with backend [P] tasks

---

## Parallel Example: User Story 1

```bash
# Tests together:
Task: "Unit test: PlacementResult derivation in backend/tests/unit/placement/test_placement_result_derivation.py"
Task: "Contract test: AssessmentAgentPort via LocalModelAdapter in backend/tests/unit/ai_agents/test_assessment_agent_port_contract.py"
Task: "Integration test: placement flow in backend/tests/integration/test_placement_flow.py"
Task: "E2E test: placement journey in frontend/tests/e2e/placement.spec.ts"

# Domain/model tasks together:
Task: "PlacementSession domain entity in backend/src/placement/domain/placement_session.py"
Task: "PlacementResult domain entity in backend/src/placement/domain/placement_result.py"
Task: "LearnerSkillProfile model + migration in backend/src/progression/infrastructure/models.py"
Task: "GamificationProfile model + migration in backend/src/gamification/infrastructure/models.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md Scenario 1 (AC-1, SC-001) independently
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. Add US1 → validate via quickstart.md Scenario 1 → demo (MVP!)
3. Add US2 → validate via quickstart.md Scenarios 2–5 → demo
4. Add US3 → validate via quickstart.md Scenarios 6–7 → demo
5. Polish → validate via quickstart.md Scenario 8 (full deterministic suite) + Scenario end-to-end run

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (placement)
   - Developer B: starts US2 domain rules/models against a stubbed placed-student fixture (doesn't block on US1 API completion)
   - Developer C: US3 adapters (isolated behind `ai_agents/ports`, no dependency on US1/US2 application code)
3. Stories integrate at the API/frontend layer once each backend slice is ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- `LearnerSkillProfile`/`GamificationProfile` models are introduced in US1 (needed for the placement bootstrap side effect) but their domain rules (level-advancement, XP, streak, badges) are US2 concerns — this split keeps US1 independently testable without pulling in US2 business logic
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same-file conflicts within a [P] group, cross-story application-code imports that break independence
