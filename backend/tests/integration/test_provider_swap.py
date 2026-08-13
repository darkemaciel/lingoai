"""Integration test (T064): switching `AI_PROVIDER` yields an identical
`POST /conversations/{id}/messages` response contract (AC-6) — proves the
API surface is unaffected by which adapter backs it. Mocks the remote
provider's SDK call directly (mirroring `test_anthropic_adapter.py`'s
approach — no real API key/network access in this environment) while still
exercising the real FastAPI app + `adapter_factory` + a real DB-backed
conversation flow.

Requires a reachable test database — skips automatically if none is
configured, per quickstart.md Scenario 8.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from anthropic.types import ToolUseBlock
from httpx import AsyncClient

from ai_agents import adapter_factory
from tests.conftest import PlacedStudent

_EXPECTED_RESPONSE_KEYS = {"agent_message", "gamification_delta"}


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestProviderSwap:
    async def test_response_contract_identical_across_local_and_anthropic(
        self, client: AsyncClient, placed_student: PlacedStudent, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        headers = _auth_headers(placed_student.token)
        start_response = await client.post("/api/v1/conversations", headers=headers)
        conversation_id = start_response.json()["conversation_session_id"]

        # --- AI_PROVIDER=local (default; LocalModelAdapter, no mocking needed) ---
        local_response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers,
            json={"client_submission_id": str(uuid.uuid4()), "content_text": "Hello!"},
        )
        assert local_response.status_code == 200, local_response.text
        assert set(local_response.json().keys()) == _EXPECTED_RESPONSE_KEYS

        # --- AI_PROVIDER=anthropic (mocked SDK call, no real network) ---
        monkeypatch.setenv("AI_PROVIDER", "anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        adapter_factory.reset_agent_adapter_cache()

        adapter = adapter_factory.get_agent_adapter()
        tool_use_block = ToolUseBlock(
            type="tool_use",
            id=str(uuid.uuid4()),
            name="emit_conversation_turn_output",
            input={
                "reply_text": "Nice to meet you!",
                "scored": False,
                "skill": None,
                "performance_score": None,
                "feedback_text": None,
            },
        )
        adapter._client.messages.create = AsyncMock(  # type: ignore[union-attr]
            return_value=SimpleNamespace(content=[tool_use_block])
        )

        anthropic_response = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=headers,
            json={"client_submission_id": str(uuid.uuid4()), "content_text": "Hello again!"},
        )
        assert anthropic_response.status_code == 200, anthropic_response.text
        assert set(anthropic_response.json().keys()) == _EXPECTED_RESPONSE_KEYS
        assert anthropic_response.json()["agent_message"]["content_text"] == "Nice to meet you!"
        # scored=False on this turn -> no gamification_delta, same contract
        # shape (key present, value null) as any other unscored turn.
        assert anthropic_response.json()["gamification_delta"] is None

        adapter_factory.reset_agent_adapter_cache()
