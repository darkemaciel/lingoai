"""Integration test (T039): submit exercise answer -> `LearningEvent`
persisted -> `feedback_text` + `gamification_delta` in the response
(AC-2, AC-3), through the real FastAPI app + a real (test-transaction-
scoped) Postgres session.

Requires a reachable test database (see conftest.py's `db_session` /
`client` / `placed_student` fixtures) — skips automatically if none is
configured, per quickstart.md Scenario 8.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from learning_content.infrastructure.seed import seed as seed_learning_content
from tests.conftest import PlacedStudent


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestActivityAnswerFlow:
    async def test_submit_answer_records_event_and_returns_feedback(
        self, client: TestClient, db_session: AsyncSession, placed_student: PlacedStudent
    ) -> None:
        await seed_learning_content(db_session)
        headers = _auth_headers(placed_student.token)

        next_response = client.get("/api/v1/activities/next", headers=headers)
        assert next_response.status_code == 200, next_response.text
        activity = next_response.json()
        assert activity["type"] in ("writing_exercise", "speaking_exercise", "listening_exercise")
        assert activity["skill"] == "writing"  # only skill bootstrapped by a text-only placement

        answer_response = client.post(
            f"/api/v1/activities/{activity['activity_id']}/answers",
            headers=headers,
            json={
                "client_submission_id": str(uuid.uuid4()),
                "response": {"text": "I go to school every day and study English with friends."},
            },
        )
        assert answer_response.status_code == 200, answer_response.text
        body = answer_response.json()
        assert isinstance(body["correct"], bool)
        assert body["feedback_text"]
        assert 0.0 <= body["performance_score"] <= 1.0
        assert body["gamification_delta"]["xp_awarded"] > 0
        assert isinstance(body["level_advanced"], bool)

        # AC-4: the scored answer is reconstructible from the LearningEvent
        # audit trail via the progression history endpoint.
        history_response = client.get(
            "/api/v1/progression/profile/writing/history", headers=headers
        )
        assert history_response.status_code == 200, history_response.text
        events = history_response.json()["events"]
        assert any(event["event_type"] == "exercise_answer_submitted" for event in events)

    async def test_answering_unknown_activity_returns_404(
        self, client: TestClient, placed_student: PlacedStudent
    ) -> None:
        response = client.post(
            f"/api/v1/activities/{uuid.uuid4()}/answers",
            headers=_auth_headers(placed_student.token),
            json={"client_submission_id": str(uuid.uuid4()), "response": {"text": "anything"}},
        )
        assert response.status_code == 404
