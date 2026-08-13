"""`AI_PROVIDER`-driven adapter selection/DI wiring (T068, research.md §1,
NFR-3). Reads the `AI_PROVIDER` env var once per process and returns the
matching concrete adapter instance, which implements all three agent
ports (`AssessmentAgentPort`, `ConversationAgentPort`,
`ProgressionSignalAgentPort` — see each adapter's own module for why one
class implements all three).

`local` (default) needs no API key and is what every deterministic test in
this codebase runs against (NFR-7); `anthropic`/`openai` require their
respective API key env var.

Application services (`placement`, `conversation`, `learning_content`) call
`get_agent_adapter()` instead of instantiating a concrete adapter
directly, so switching `AI_PROVIDER` and restarting the backend is the
only step needed to change provider (AC-6, quickstart.md Scenario 6:
"restart backend only") — no application-layer code changes. The
process-wide caching below is deliberate for exactly that reason: a
provider swap is expected to take effect on restart, not mid-process.
"""

from __future__ import annotations

import os
from typing import Protocol

from ai_agents.adapters.local_model_adapter import LocalModelAdapter
from ai_agents.observability.agent_invocation_log import AgentProvider
from ai_agents.ports.assessment_agent_port import AssessmentAgentPort
from ai_agents.ports.conversation_agent_port import ConversationAgentPort
from ai_agents.ports.progression_signal_agent_port import ProgressionSignalAgentPort


class AgentAdapter(
    AssessmentAgentPort, ConversationAgentPort, ProgressionSignalAgentPort, Protocol
):
    """Structural union of all three agent ports — every concrete adapter
    (`LocalModelAdapter`, `AnthropicAdapter`, `OpenAIAdapter`) satisfies
    this by implementing all three."""


class UnknownAIProviderError(Exception):
    pass


_SUPPORTED_PROVIDERS = ("local", "anthropic", "openai")

_PROVIDER_TO_LOG_ENUM: dict[str, AgentProvider] = {
    "local": AgentProvider.LOCAL_MOCK,
    "anthropic": AgentProvider.ANTHROPIC,
    "openai": AgentProvider.OPENAI,
}

_cached_adapter: AgentAdapter | None = None


def _build_adapter(provider: str) -> AgentAdapter:
    if provider == "local":
        return LocalModelAdapter()
    if provider == "anthropic":
        from ai_agents.adapters.anthropic_adapter import AnthropicAdapter

        return AnthropicAdapter()
    if provider == "openai":
        from ai_agents.adapters.openai_adapter import OpenAIAdapter

        return OpenAIAdapter()
    raise UnknownAIProviderError(
        f"unknown AI_PROVIDER '{provider}' (expected one of {_SUPPORTED_PROVIDERS})"
    )


def get_agent_adapter() -> AgentAdapter:
    """Returns the process-wide adapter instance for the configured
    `AI_PROVIDER`, building it lazily on first call and reusing it after."""
    global _cached_adapter
    if _cached_adapter is None:
        provider = os.environ.get("AI_PROVIDER", "local").lower()
        _cached_adapter = _build_adapter(provider)
    return _cached_adapter


def current_agent_provider() -> AgentProvider:
    """The `AgentProvider` enum value matching the currently-configured
    `AI_PROVIDER`, for `AgentInvocationLog` tagging (NFR-4) at each
    application-service call site."""
    provider = os.environ.get("AI_PROVIDER", "local").lower()
    if provider not in _PROVIDER_TO_LOG_ENUM:
        raise UnknownAIProviderError(
            f"unknown AI_PROVIDER '{provider}' (expected one of {_SUPPORTED_PROVIDERS})"
        )
    return _PROVIDER_TO_LOG_ENUM[provider]


def reset_agent_adapter_cache() -> None:
    """Test-only: clears the cached instance so a test can reconfigure
    `AI_PROVIDER` and get a freshly built adapter (T064's provider-swap
    integration test)."""
    global _cached_adapter
    _cached_adapter = None
