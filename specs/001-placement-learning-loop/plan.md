# Implementation Plan: Placement & Learning Loop

**Branch**: `001-placement-learning-loop` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-placement-learning-loop/spec.md`

## Summary

First vertical slice of LingoAI: a student registers, is automatically guided through an AI-led placement conversation that produces a per-skill CEFR level, then enters a continuous learning loop (conversation + writing/speaking/listening exercises) where every answer produces pedagogical feedback and an immutable `LearningEvent`. A deterministic domain rule (not the LLM) decides level advancement from a windowed accuracy signal, and never regresses a level. Progression is reinforced with a moderate, non-competitive gamification layer (XP, daily streak, milestone badges) shown inline after each activity and in a persistent panel. Technical approach: Python/FastAPI modular monolith (Clean Architecture, one module per bounded context) behind a Next.js web client, PostgreSQL as the only data store (operational + append-only event log), all AI/STT/TTS access behind provider-swappable ports, running fully local via Docker Compose.

## Technical Context

**Language/Version**: TypeScript 5.x (Next.js 14+) — frontend; Python 3.12 — backend

**Primary Dependencies**: Next.js/React (frontend); FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic, `anthropic` SDK, `openai` SDK (backend) — see research.md §1, §8

**Storage**: PostgreSQL 16 (+ `pgvector` extension); no separate cache/session store this iteration (research.md §5)

**Testing**: pytest + pytest-asyncio + httpx (backend unit/integration); vcrpy-style recorded cassettes for AI-adapter tests (NFR-7); Vitest + React Testing Library (frontend unit); Playwright (E2E against full Docker Compose stack) — research.md §9

**Target Platform**: Docker Compose (Linux containers) for backend + PostgreSQL; any evergreen browser for the Next.js frontend

**Project Type**: Web application (frontend + backend)

**Performance Goals**: Conversation turn (student message → agent reply) ≤ ~3s under local/standard-provider conditions (NFR-5)

**Constraints**: Fully local via `docker compose up`, no cloud dependency except the outbound AI provider call (NFR-1); no business rule may depend on a proprietary cloud/AI-vendor feature (NFR-2); all secrets via env vars (NFR-3); every agent call structured-logged via `AgentInvocationLog` (NFR-4); auth + TLS in transit for learner data (NFR-6); level advancement is domain-rule-driven and auditable, never regresses (FR-9)

**Scale/Scope**: MVP, local-first, single-instance; no explicit concurrent-user target this iteration (deferred to the future cloud-deploy spec per spec.md Assumptions) — this slice covers registration/auth, placement, the conversation+exercise loop, and the gamification layer (XP/streak/badges) only

All Technical Context unknowns are resolved in [research.md](./research.md) (LLM/STT/TTS providers §1–2, REST vs GraphQL §3, CEFR+mastery scale §4, cache strategy §5, level-advancement rule §6, XP formula §7, module boundaries §8, testing tooling §9, auth mechanism §10).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution principle | Gate | Status |
|---|---|---|
| §1 Product Principle | AI must not unilaterally decide progression | **PASS** — level advancement is a deterministic domain rule (research.md §6); agents only emit `performance_score` signals (contracts/agent-ports.md) |
| §3 Architecture | Clean Architecture, DDD, modular monolith, dependencies point inward | **PASS** — 6 bounded-context modules, each layered `domain/application/infrastructure/api`, cross-module contact only via `LearningEvent`/application calls (research.md §8) |
| §4 Client Independence | Domain independent of client; API supports future mobile without rework | **PASS** — REST contract is bearer-token based, not cookie-only (research.md §10); no client-specific logic in domain modules |
| §5 AI Architecture | Each agent: single responsibility, explicit I/O, independent testing, replaceable provider | **PASS** — 3 agent ports + 2 audio ports, each with a documented input/output contract (contracts/agent-ports.md); 3 interchangeable adapters exercise AC-6 for real |
| §6 Technology Principles | Open-source preferred, vendor independence, no premature optimization | **PARTIAL, justified** — LLM APIs (Anthropic/OpenAI) are inherently hosted/proprietary; mitigated by full adapter isolation (§5) and a `LocalModelAdapter` fallback path (NFR-1). Everything else (FastAPI, Next.js, PostgreSQL, Alembic) is open-source. No Redis/cache added without justified need (research.md §5) |
| §7 Environment Independence | Runs fully local, cloud deploy needs no code change | **PASS** — Docker Compose is the only runtime dependency besides the AI provider call (quickstart.md) |
| §8 Configuration | No hardcoded secrets | **PASS** — all keys/DB creds via env vars (`.env`), never committed |
| §9 Database Principles | Migrations, version-controlled schema, operational/analytical separation | **PASS** — Alembic migrations; `LearningEvent` (analytical, append-only) explicitly separated from operational tables (data-model.md) |
| §10 Engineering Quality | Simplicity first, complexity justified | **PASS** — no microservices/queues introduced (see Complexity Tracking: none needed) |
| §11 Testing Principles | Pyramid, deterministic, LLM calls mocked/recorded | **PASS** — `LocalModelAdapter` deterministic by default; cassette-based tests for real adapters only in a separate tagged suite (research.md §9, contracts/agent-ports.md) |
| §12 Data Principles | Event-driven learning progress, immutable events, operational/analytical split | **PASS** — `LearningEvent` is the single source of truth; `LearnerSkillProfile`/`GamificationProfile` are rebuildable projections (data-model.md) |
| §13 Security | AuthN/Z, input validation, least privilege | **PASS** — JWT bearer auth, bcrypt hashing, TLS assumed at the edge (research.md §10) |
| §14 API Principles | Explicit, versionable contracts, no internal leakage | **PASS** — `/api/v1` prefix, no domain/infra details in responses (contracts/rest-api.md) |
| §17 MVP Principle | Smallest solution satisfying the spec, no premature distributed systems | **PASS** — single Postgres instance, no message queue, no second data store |

No unjustified violations. The single **PARTIAL** (§6, hosted AI provider) is the standard, unavoidable tradeoff of using generative AI at all and is fully isolated behind ports/adapters per §5 — documented here rather than in the Complexity Tracking table below, since it isn't an *architectural complexity* addition, just a vendor-dependency fact.

*(Re-checked post-Phase 1 — see "Post-Design Constitution Re-check" at the end of this document.)*

## Project Structure

### Documentation (this feature)

```text
specs/001-placement-learning-loop/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/             # Phase 1 output (/speckit-plan command)
│   ├── rest-api.md
│   └── agent-ports.md
└── tasks.md               # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── identity/
│   │   ├── domain/            # User, credential rules
│   │   ├── application/       # register/login/refresh use cases
│   │   ├── infrastructure/    # SQLAlchemy models, bcrypt, JWT issuance
│   │   └── api/                # /api/v1/auth routes
│   ├── placement/
│   │   ├── domain/            # PlacementSession/PlacementResult rules
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/                # /api/v1/placement routes
│   ├── conversation/
│   │   ├── domain/            # ConversationSession/Message
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/                # /api/v1/conversations routes
│   ├── progression/
│   │   ├── domain/            # LearnerSkillProfile, windowed-accuracy rule (research.md §6)
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/                # /api/v1/progression routes
│   ├── gamification/
│   │   ├── domain/            # GamificationProfile, XP formula (research.md §7), streak rule, Badge
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/                # /api/v1/gamification routes
│   ├── learning_content/
│   │   ├── domain/            # LearningPath/Unit/Activity
│   │   ├── application/
│   │   ├── infrastructure/
│   │   └── api/                # /api/v1/activities routes
│   ├── ai_agents/
│   │   ├── ports/              # AgentPort protocols per agent + audio provider protocols (contracts/agent-ports.md)
│   │   ├── adapters/           # AnthropicAdapter, OpenAIAdapter, LocalModelAdapter, NullAudioAdapter
│   │   └── observability/      # AgentInvocationLog writer (shared by all ports)
│   ├── shared_kernel/          # base entity/value-object types, domain event bus (publishes LearningEvent)
│   └── app.py                  # FastAPI app assembly / DI wiring
├── migrations/                  # Alembic
└── tests/
    ├── unit/                    # per-module domain rules, agent contract tests (LocalModelAdapter)
    ├── integration/              # API → domain → DB flows
    └── contract/                  # cassette-based adapter tests (Anthropic/OpenAI), tagged separately

frontend/
├── src/
│   ├── app/                     # Next.js app router: auth, placement, learn, progress panel
│   ├── components/              # incl. inline gamification feedback component (FR-19)
│   ├── services/                 # API client (typed from contracts/rest-api.md)
│   └── ...
└── tests/
    ├── unit/                    # Vitest + RTL
    └── e2e/                      # Playwright, run against docker compose stack

docker-compose.yml                # frontend, backend, postgres (Redis service intentionally omitted — research.md §5)
```

**Structure Decision**: Web application (Option 2: frontend + backend), backend organized as a modular monolith with one Clean-Architecture-layered module per bounded context (research.md §8), matching spec.md's Technology Choices table 1:1. No `src/` single-project layout applies since this is a two-client-surface (web now, mobile later) system per Constitution §4.

## Complexity Tracking

*No entries — Constitution Check reported no unjustified violations.* The one deviation worth naming (§6, hosted AI provider dependency) is a vendor-neutrality mitigation already covered under §5's port/adapter isolation, not an added architectural complexity (no extra project, no extra data store, no distributed component beyond what spec.md's Technology Choices table already specifies).

## Post-Design Constitution Re-check

Re-evaluated after Phase 1 (`data-model.md`, `contracts/`, `quickstart.md`):

- **§1/§5/§9 (progression auditability)**: confirmed at the data level — `LearningEvent` is append-only with an idempotency key, `LearnerSkillProfile` is an explicitly rebuildable projection, and the level-advancement rule lives in `progression/domain/` with zero agent-port dependency (data-model.md, contracts/agent-ports.md). No drift from the pre-design gate.
- **§12 (event-driven, operational/analytical split)**: `LearningEvent` table is structurally separated from operational tables (`LearnerSkillProfile`, `GamificationProfile`) which are marked as projections, not sources of truth — confirmed in data-model.md.
- **§14 (API contracts, no internal leakage)**: `contracts/rest-api.md`'s "Cross-cutting" section explicitly excludes `password_hash`, raw prompts/completions, and `AgentInvocationLog` from any response — confirmed.
- **§17 (MVP simplicity)**: no new infrastructure component was introduced during design (still Postgres + the two app containers); Redis remains explicitly deferred (research.md §5).
- **No new violations introduced during Phase 1 design.** Constitution Check result stands: **PASS**, with the one pre-existing, isolated §6 PARTIAL noted above.
