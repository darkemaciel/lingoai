# Phase 1 Data Model: Placement & Learning Loop

Source: `spec.md` §Key Entities, resolved against `research.md` decisions (§4 CEFR+mastery, §6 windowed accuracy rule, §7 XP formula, §8 module boundaries).

Naming note: spec.md's `LearnerProfile` is the *per-user aggregate view* across skills; the entity actually persisted, one row per (user, skill), is `LearnerSkillProfile` below — a student has up to 4 rows (reading/writing/speaking/listening).

## Entity Relationship Overview

```text
User 1──1 GamificationProfile
User 1──N LearnerSkillProfile        (one per skill: reading/writing/speaking/listening)
User 1──N PlacementSession
User 1──N ConversationSession
User 1──N LearningEvent
User 1──N BadgeAward

PlacementSession 1──1 PlacementResult
PlacementResult  ──seeds──> LearnerSkillProfile (bootstrap, one-time)

LearningPath 1──N Unit 1──N Activity
Activity 1──N LearningEvent (via activity_id, nullable)
ConversationSession 1──N Message
ConversationSession 1──N LearningEvent (via conversation_session_id, nullable)

Badge 1──N BadgeAward
BadgeAward N──1 User

AgentInvocationLog ──references (informational only, no FK)── User / Activity / ConversationSession
```

All modules communicate across boundaries only via `LearningEvent` (published on the shared kernel's domain event bus) or explicit application-layer calls — never direct cross-module table joins in domain code (Constitution §3).

---

## User

Identity module. Account and profile basics.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| email | string, unique | validated format; login identifier |
| password_hash | string | bcrypt hash, never the plaintext |
| native_language | string (ISO 639-1), nullable | for future localization, not used in MVP UI |
| timezone | string (IANA tz name) | used for streak day-boundary calculation (research §7 reset rule) |
| created_at | timestamp | |

**Validation**: `email` unique and RFC-valid; `password_hash` never null once account is active.

---

## PlacementSession

Placement (Nivelamento) module.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| status | enum: `in_progress`, `completed`, `abandoned` | |
| modality | enum: `text_only`, `text_and_audio` | reflects whether audio was actually used (FR-3, edge case: no mic available) |
| started_at | timestamp | |
| completed_at | timestamp, nullable | set only when `status = completed` |

**State transitions**: `in_progress → completed` (normal path) or `in_progress → abandoned` (session inactive beyond a configurable timeout, or student explicitly restarts — per spec Edge Case "retomar ou reiniciar de forma clara"). Terminal states (`completed`, `abandoned`) do not transition further; a new session is created if the student restarts.

---

## PlacementResult

Placement module. Generated once per completed `PlacementSession`.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| placement_session_id | UUID (FK → PlacementSession, unique) | 1:1 |
| reading_level | enum CEFR (`A1`…`C2`) | |
| writing_level | enum CEFR | |
| speaking_level | enum CEFR, nullable | null if no audio modality used (FR-3) |
| listening_level | enum CEFR, nullable | null if no audio modality used |
| strengths_summary | text | student-facing (FR-5) |
| weaknesses_summary | text | student-facing (FR-5) |
| generated_at | timestamp | |

**Validation**: only creatable when `placement_session.status = completed`. Immutable once created (a re-placement, if ever supported, creates a new `PlacementSession`/`PlacementResult` pair, not an edit).

**Side effect**: creation bootstraps one `LearnerSkillProfile` row per non-null skill level (CEFR level = the placement result; `mastery_score = 0`), and one `GamificationProfile` row if the user doesn't have one yet.

---

## LearnerSkillProfile

Progression module. One row per (user, skill) — the persisted form of spec.md's `LearnerProfile`.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| skill | enum: `reading`, `writing`, `speaking`, `listening` | |
| cefr_level | enum CEFR | |
| mastery_score | int, 0–100 | progress within the current CEFR level; drives activity difficulty selection (FR-7) |
| accuracy_window | JSON array, max 10 entries of `{correct: bool, at: timestamp}` | denormalized projection of the last 10 scored `LearningEvent`s for this skill — cache, not source of truth |
| updated_at | timestamp | |

**Unique constraint**: (`user_id`, `skill`).

**State transitions** (enforced by the Progression domain rule, research §6):
- `cefr_level` advances one step (e.g. `A2 → B1`) only when `accuracy_window` has ≥ 5 entries and accuracy ≥ 80%. On advance: `cefr_level` moves forward, `mastery_score` resets to 0, `accuracy_window` clears (fresh tracking in the new level).
- `cefr_level` **never decreases**. Weak performance only lowers `mastery_score`/leaves the window below threshold, which biases activity selection (FR-7) toward reinforcement — it never triggers a transition backward.
- Every scored `LearningEvent` for this skill appends to `accuracy_window` (dropping the oldest entry beyond 10) and recomputes `mastery_score`.

---

## LearningPath / Unit / Activity

Shared read model (`learning_content` module) consumed by `conversation` and `progression`.

**LearningPath**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| skill | enum: reading/writing/speaking/listening | |
| cefr_level | enum CEFR | |
| name | string | |

**Unit**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| learning_path_id | UUID (FK → LearningPath) | |
| sequence_order | int | ordering within the path |
| name | string | |

**Activity**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| unit_id | UUID (FK → Unit) | |
| type | enum: `conversation_prompt`, `writing_exercise`, `speaking_exercise`, `listening_exercise` | drives `base_xp` lookup (research §7) |
| prompt_content | JSON | agent-consumable prompt/rubric definition |
| difficulty_hint | int, 0–100 | maps roughly to target `mastery_score` band |

**Validation**: `Activity.type` must be compatible with the skill of its parent `Unit → LearningPath` (e.g. `writing_exercise` only inside a `writing` path); `conversation_prompt` activities may target multiple skills at once (the agent tags which skill(s) each resulting `LearningEvent` applies to).

---

## ConversationSession / Message

Conversation module.

**ConversationSession**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| status | enum: `active`, `ended` | |
| started_at | timestamp | |
| last_message_at | timestamp | |

**Message**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| conversation_session_id | UUID (FK → ConversationSession) | |
| sender | enum: `student`, `agent` | |
| content_text | text | always present, even for audio messages (transcribed) |
| audio_ref | string (URI), nullable | reference to stored audio, when applicable (FR-14) |
| created_at | timestamp | |

---

## LearningEvent

Analytical/event module (Constitution §12). **Append-only; no `UPDATE`/`DELETE` in application code.**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| event_type | enum: `placement_answer_submitted`, `exercise_answer_submitted`, `conversation_turn_completed`, `level_advanced`, `badge_awarded` | |
| skill | enum, nullable | applicable skill, when relevant |
| activity_id | UUID (FK → Activity), nullable | |
| placement_session_id | UUID (FK → PlacementSession), nullable | |
| conversation_session_id | UUID (FK → ConversationSession), nullable | |
| client_submission_id | UUID | client-generated idempotency key |
| payload | JSONB | `{ raw_response, performance_score: 0..1, feedback_text, time_spent_ms, attempt_number }` (shape varies slightly by `event_type`) |
| created_at | timestamp | immutable |

**Validation / idempotency**: unique constraint on (`user_id`, `client_submission_id`) — a duplicate submission (spec Edge Case: rapid double-send) upserts to the same event rather than creating a second one, so downstream projections (`LearnerSkillProfile`, `GamificationProfile`) are never double-counted.

**This table is the single source of truth** `LearnerSkillProfile` and `GamificationProfile` are projected from — both are safely rebuildable by replaying it (Rollback Considerations in spec.md).

---

## GamificationProfile

Gamification module. One row per user.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User, unique) | 1:1 |
| xp_total | int | sum of all `xp_awarded` (research §7) |
| streak_current | int | consecutive days with ≥1 completed activity |
| streak_last_activity_date | date | in the user's `timezone`; used to detect a missed day |
| updated_at | timestamp | |

**State transitions**:
- On each qualifying `LearningEvent`: `xp_total += xp_awarded` (research §7 formula); if `streak_last_activity_date` is yesterday, `streak_current += 1`; if it's today, no change; if older than yesterday, `streak_current` resets to `1` (today's activity starts a new streak) — no tolerance/freeze (Clarifications).
- `streak_current` is never decremented by a background job — it is only ever recomputed lazily on the next qualifying activity, comparing `streak_last_activity_date` to "today" in the user's timezone.

---

## Badge / BadgeAward

Gamification module.

**Badge** (catalog, seed data — not user-generated)

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| code | string, unique | e.g. `first_conversation_completed`, `streak_7_days`, `first_level_advanced` |
| name | string | student-facing |
| description | string | student-facing |
| criteria_description | string | internal/dev-facing, describes the trigger rule |

**BadgeAward**

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| user_id | UUID (FK → User) | |
| badge_id | UUID (FK → Badge) | |
| awarded_at | timestamp | |

**Unique constraint**: (`user_id`, `badge_id`) — a badge is awarded at most once per student.

---

## AgentInvocationLog

AI Agents module. Observability only (Constitution §5, §10, NFR-4) — never read by domain logic.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| agent_name | enum: `assessment_agent`, `conversation_agent`, `progression_agent` | |
| provider | enum: `anthropic`, `openai`, `local_mock` | which adapter served the call (research §1) |
| input_summary | text | truncated/redacted, no raw PII |
| output_summary | text | truncated |
| latency_ms | int | |
| success | bool | |
| error_message | text, nullable | |
| created_at | timestamp | |
