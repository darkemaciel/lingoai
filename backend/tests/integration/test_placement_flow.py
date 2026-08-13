"""Integration test (T021): POST /placement/sessions -> POST .../answers
(loop to completion) -> GET .../result, through the real FastAPI app + a
real (test-transaction-scoped) Postgres session (AC-1, AC-2).

Requires a reachable test database (see conftest.py's `db_session` /
`client` fixtures) — skips automatically if none is configured, per
quickstart.md Scenario 8's "full suite passes with AI_PROVIDER=local"
running inside `docker compose exec backend pytest` where Postgres is
always up.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from ai_agents.adapters.local_model_adapter import ASSESSMENT_TURNS_BEFORE_COMPLETE
from identity.infrastructure.security import create_access_token


async def _register_and_authenticate(client: AsyncClient) -> tuple[str, str]:
    """Register a fresh user directly against the DB-backed auth flow and
    return (user_id, bearer_token). Bypasses /auth/login (also DB-backed,
    exercised separately by identity's own tests) to keep this test
    focused on the placement flow itself."""
    email = f"placement-{uuid.uuid4()}@example.com"
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "s3cret!!!"}
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["user_id"]
    access_token, _ = create_access_token(uuid.UUID(user_id))
    return user_id, access_token


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestPlacementFlow:
    async def test_full_placement_flow_produces_result_and_seeds_profiles(
        self, client: AsyncClient
    ) -> None:
        _, token = await _register_and_authenticate(client)
        headers = _auth_headers(token)

        start_response = await client.post("/api/v1/placement/sessions", headers=headers)
        assert start_response.status_code == 201, start_response.text
        body = start_response.json()
        assert body["status"] == "in_progress"
        assert body["modality"] == "text_only"
        session_id = body["placement_session_id"]

        session_status = "in_progress"
        for turn in range(ASSESSMENT_TURNS_BEFORE_COMPLETE):
            answer_response = await client.post(
                f"/api/v1/placement/sessions/{session_id}/answers",
                headers=headers,
                json={
                    "client_submission_id": str(uuid.uuid4()),
                    "content_text": f"My answer for turn {turn}",
                },
            )
            assert answer_response.status_code == 200, answer_response.text
            answer_body = answer_response.json()
            session_status = answer_body["session_status"]

        assert session_status == "completed"
        assert answer_body["next_prompt"] is None

        result_response = await client.get(
            f"/api/v1/placement/sessions/{session_id}/result", headers=headers
        )
        assert result_response.status_code == 200, result_response.text
        result_body = result_response.json()
        assert result_body["reading_level"]
        assert result_body["writing_level"]
        # LocalModelAdapter only populates speaking/listening when this
        # turn's `audio_transcript` was set — this flow never sends audio.
        assert result_body["speaking_level"] is None
        assert result_body["listening_level"] is None
        assert result_body["strengths_summary"]
        assert result_body["weaknesses_summary"]

        profile_response = await client.get("/api/v1/progression/profile", headers=headers)
        assert profile_response.status_code == 200, profile_response.text
        skills = {row["skill"]: row for row in profile_response.json()["skills"]}
        assert "reading" in skills
        assert "writing" in skills
        assert skills["reading"]["mastery_score"] == 0
        assert skills["reading"]["cefr_level"] == result_body["reading_level"]

    async def test_duplicate_client_submission_id_is_idempotent(
        self, client: AsyncClient
    ) -> None:
        _, token = await _register_and_authenticate(client)
        headers = _auth_headers(token)

        start_response = await client.post("/api/v1/placement/sessions", headers=headers)
        session_id = start_response.json()["placement_session_id"]

        submission_id = str(uuid.uuid4())
        first = await client.post(
            f"/api/v1/placement/sessions/{session_id}/answers",
            headers=headers,
            json={"client_submission_id": submission_id, "content_text": "first send"},
        )
        second = await client.post(
            f"/api/v1/placement/sessions/{session_id}/answers",
            headers=headers,
            json={"client_submission_id": submission_id, "content_text": "first send"},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

    async def test_result_not_available_before_completion(self, client: AsyncClient) -> None:
        _, token = await _register_and_authenticate(client)
        headers = _auth_headers(token)

        start_response = await client.post("/api/v1/placement/sessions", headers=headers)
        session_id = start_response.json()["placement_session_id"]

        result_response = await client.get(
            f"/api/v1/placement/sessions/{session_id}/result", headers=headers
        )
        assert result_response.status_code == 409

    async def test_answers_on_someone_elses_session_returns_404(
        self, client: AsyncClient
    ) -> None:
        _, owner_token = await _register_and_authenticate(client)
        _, other_token = await _register_and_authenticate(client)

        start_response = await client.post(
            "/api/v1/placement/sessions", headers=_auth_headers(owner_token)
        )
        session_id = start_response.json()["placement_session_id"]

        response = await client.post(
            f"/api/v1/placement/sessions/{session_id}/answers",
            headers=_auth_headers(other_token),
            json={"client_submission_id": str(uuid.uuid4()), "content_text": "intruder"},
        )
        assert response.status_code == 404
