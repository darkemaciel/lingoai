# REST API Contract: Placement & Learning Loop

Generated from FastAPI (OpenAPI is the executable source of truth once implemented); this document fixes the contract shape so client and backend work can proceed in parallel. All authenticated endpoints accept `Authorization: Bearer <access_token>` (research.md §10) — the web client also gets it via an httpOnly cookie through its BFF route, but the underlying API contract is header-based so a future mobile client needs no contract change (NFR-8).

Versioning: all paths prefixed `/api/v1`. Breaking changes require a `/api/v2` path and a spec update (Constitution §14).

---

## Identity

### `POST /api/v1/auth/register`
Request: `{ email: string, password: string }`
Response `201`: `{ user_id: uuid, email: string }`
Errors: `409` email already registered; `422` validation.

### `POST /api/v1/auth/login`
Request: `{ email: string, password: string }`
Response `200`: `{ access_token: string, refresh_token: string, expires_in: int }`
Errors: `401` invalid credentials.

### `POST /api/v1/auth/refresh`
Request: `{ refresh_token: string }`
Response `200`: `{ access_token: string, expires_in: int }`
Errors: `401` invalid/expired/revoked refresh token.

---

## Placement (Nivelamento)

### `POST /api/v1/placement/sessions`
Starts a placement session (FR-2, auto-triggered on first login by the client right after registration/first login).
Response `201`: `{ placement_session_id: uuid, status: "in_progress", modality: "text_only" | "text_and_audio" }`

### `POST /api/v1/placement/sessions/{id}/answers`
Submits one answer within the placement conversation (text and/or audio, FR-3).
Request: `{ client_submission_id: uuid, content_text: string, audio_ref?: string }`
Response `200`: `{ next_prompt: { content_text: string, audio_ref?: string } | null, session_status: "in_progress" | "completed" }`
`next_prompt: null` signals the placement is finished; the client then calls the result endpoint.
Errors: `404` session not found/not owned by caller; `409` session already `completed`/`abandoned`.

### `GET /api/v1/placement/sessions/{id}/result`
Response `200` (only once `status = completed`): `PlacementResult` shape — `{ reading_level, writing_level, speaking_level, listening_level, strengths_summary, weaknesses_summary }` (FR-5, AC-1).
Errors: `409` session not completed yet.

---

## Learning Loop (Conversation + Exercises)

### `POST /api/v1/conversations`
Starts (or resumes the active) conversation session (FR-6).
Response `201`: `{ conversation_session_id: uuid }`

### `POST /api/v1/conversations/{id}/messages`
Sends a student message (text and/or audio).
Request: `{ client_submission_id: uuid, content_text: string, audio_ref?: string }`
Response `200`: `{ agent_message: { content_text: string, audio_ref?: string }, gamification_delta?: GamificationDelta }`
`gamification_delta` present when this turn generated a scored `LearningEvent` (research §7) — see shape below. Response budget: ≤ ~3s (NFR-5).

### `GET /api/v1/activities/next`
Returns the next recommended activity per FR-7 (writing/speaking/listening exercise), chosen from `LearnerSkillProfile.mastery_score`/`cefr_level`.
Response `200`: `{ activity_id: uuid, type: "writing_exercise" | "speaking_exercise" | "listening_exercise", skill: string, prompt_content: object }`

### `POST /api/v1/activities/{id}/answers`
Submits an answer to an exercise (FR-8).
Request: `{ client_submission_id: uuid, response: object }` (`response` shape depends on activity type)
Response `200`:
```json
{
  "correct": true,
  "feedback_text": "string explaining the error/correction (FR-8, AC-3)",
  "performance_score": 0.0,
  "gamification_delta": { "xp_awarded": 0, "xp_total": 0, "streak_current": 0, "badges_unlocked": ["code"] },
  "level_advanced": false
}
```
Idempotent on `client_submission_id` (spec Edge Case: duplicate submission).

---

## Progression & Gamification (read models)

### `GET /api/v1/progression/profile`
Response `200`: `{ skills: [ { skill, cefr_level, mastery_score } ] }` — AC-4's auditable-progress read model (backed by `LearnerSkillProfile`).

### `GET /api/v1/progression/profile/{skill}/history`
Response `200`: paginated list of the `LearningEvent`s that fed the current `cefr_level` for that skill — the concrete mechanism behind AC-4 ("reconstruir/justificar por que o LearnerProfile está no nível atual").

### `GET /api/v1/gamification/profile`
The persistent progress panel (FR-19, SC-007).
Response `200`: `{ xp_total: int, streak_current: int, badges: [ { code, name, description, awarded_at } ] }`

**`GamificationDelta` shape** (embedded in the two endpoints above that award XP):
```json
{ "xp_awarded": 10, "xp_total": 145, "streak_current": 4, "badges_unlocked": ["first_conversation_completed"] }
```

---

## Cross-cutting

- All list endpoints are paginated (`?cursor=&limit=`), default `limit=20`, max `100`.
- All error responses share the shape `{ "error": { "code": string, "message": string } }`.
- No endpoint ever exposes `password_hash`, raw agent prompts/completions, or `AgentInvocationLog` rows (internal-only, Constitution §14 "no leaking internal implementation details").
