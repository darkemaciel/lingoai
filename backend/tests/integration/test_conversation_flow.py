"""Integration test (T041): conversation turn end-to-end — message ->
agent reply, and scored turns produce a `LearningEvent` (NFR-5's ~3s
budget isn't measured here, `LocalModelAdapter` has no network latency by
construction; this test asserts the functional contract only).

Requires a reachable test database — skips automatically if none is
configured, per quickstart.md Scenario 8.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.conftest import PlacedStudent


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestConversationFlow:
    async def test_start_conversation_resumes_active_session(
        self, client: AsyncClient, placed_student: PlacedStudent
    ) -> None:
        headers = _auth_headers(placed_student.token)
        first = await client.post("/api/v1/conversations", headers=headers)
        second = await client.post("/api/v1/conversations", headers=headers)
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["conversation_session_id"] == second.json()["conversation_session_id"]

    async def test_first_turn_is_scored_and_produces_learning_event(
        self, client: AsyncClient, placed_student: PlacedStudent
    ) -> None:
        headers = _auth_headers(placed_student.token)
        start_response = await client.post("/api/v1/conversations", headers=headers)
        conversation_id = start_response.json()["conversation_session_id"]

        response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers,
            json={
                "client_submission_id": str(uuid.uuid4()),
                "content_text": "I would like to practice my writing skills today.",
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["agent_message"]["content_text"]
        # LocalModelAdapter scores the very first turn of a conversation
        # (empty history -> len(history) % 2 == 0).
        assert body["gamification_delta"] is not None
        assert body["gamification_delta"]["xp_awarded"] > 0

        # LocalModelAdapter picks whichever skill happens to be first in
        # the learner's context (reading or writing — both bootstrapped by
        # a text-only placement); check both rather than assume an order.
        matching_events = []
        for skill in ("reading", "writing"):
            history_response = await client.get(
                f"/api/v1/progression/profile/{skill}/history", headers=headers
            )
            matching_events.extend(
                event
                for event in history_response.json()["events"]
                if event["event_type"] == "conversation_turn_completed"
            )
        assert matching_events

    async def test_message_on_someone_elses_conversation_returns_404(
        self, client: AsyncClient, placed_student: PlacedStudent
    ) -> None:
        owner_headers = _auth_headers(placed_student.token)
        start_response = await client.post("/api/v1/conversations", headers=owner_headers)
        conversation_id = start_response.json()["conversation_session_id"]

        email = f"intruder-{uuid.uuid4()}@example.com"
        register_response = await client.post(
            "/api/v1/auth/register", json={"email": email, "password": "s3cret!!!"}
        )
        assert register_response.status_code == 201
        login_response = await client.post(
            "/api/v1/auth/login", json={"email": email, "password": "s3cret!!!"}
        )
        intruder_token = login_response.json()["access_token"]

        response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=_auth_headers(intruder_token),
            json={"client_submission_id": str(uuid.uuid4()), "content_text": "intruder"},
        )
        assert response.status_code == 404
