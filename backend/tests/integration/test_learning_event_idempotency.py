"""Integration test (T040): duplicate `client_submission_id` on an
exercise answer is idempotent — no double-counted XP/profile update
(spec Edge Case: rapid double-send). Placement's own idempotency is
already covered by `test_placement_flow.py`; this covers the shared
`LearningEvent` recorder (T050) path used by the learning-loop endpoints.

Requires a reachable test database — skips automatically if none is
configured, per quickstart.md Scenario 8.
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from learning_content.infrastructure.seed import seed as seed_learning_content
from tests.conftest import PlacedStudent


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestLearningEventIdempotency:
    async def test_duplicate_activity_answer_does_not_double_count_xp(
        self, client: AsyncClient, db_session: AsyncSession, placed_student: PlacedStudent
    ) -> None:
        await seed_learning_content(db_session)
        headers = _auth_headers(placed_student.token)

        activity_response = await client.get("/api/v1/activities/next", headers=headers)
        activity = activity_response.json()
        submission_id = str(uuid.uuid4())
        payload = {
            "client_submission_id": submission_id,
            "response": {"text": "I go to school every day and study English with friends."},
        }

        first = await client.post(
            f"/api/v1/activities/{activity['activity_id']}/answers", headers=headers, json=payload
        )
        second = await client.post(
            f"/api/v1/activities/{activity['activity_id']}/answers", headers=headers, json=payload
        )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        first_xp_total = first.json()["gamification_delta"]["xp_total"]
        second_xp_total = second.json()["gamification_delta"]["xp_total"]
        assert first_xp_total == second_xp_total

        profile_response = await client.get("/api/v1/gamification/profile", headers=headers)
        profile = profile_response.json()
        assert profile["xp_total"] == first_xp_total

        history_response = await client.get(
            "/api/v1/progression/profile/writing/history", headers=headers
        )
        events = history_response.json()["events"]
        scored_events = [
            event for event in events if event["event_type"] == "exercise_answer_submitted"
        ]
        assert len(scored_events) == 1

    async def test_duplicate_conversation_message_does_not_double_count_xp(
        self, client: AsyncClient, placed_student: PlacedStudent
    ) -> None:
        headers = _auth_headers(placed_student.token)
        start_response = await client.post("/api/v1/conversations", headers=headers)
        conversation_id = start_response.json()["conversation_session_id"]

        submission_id = str(uuid.uuid4())
        payload = {"client_submission_id": submission_id, "content_text": "Hello there!"}

        first = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages", headers=headers, json=payload
        )
        second = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages", headers=headers, json=payload
        )

        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        first_reply = first.json()["agent_message"]["content_text"]
        second_reply = second.json()["agent_message"]["content_text"]
        assert first_reply == second_reply
