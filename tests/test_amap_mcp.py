from __future__ import annotations

from types import SimpleNamespace

import pytest

from restaurant_agent.amap_mcp import AmapMCPConfig, create_amap_mcp_server
from restaurant_agent.agent import RestaurantAgentService
from restaurant_agent.api import create_default_agent_service
from restaurant_agent.contracts import ChatRequest, ChatResponse
from restaurant_agent.providers import SampleRestaurantProvider
from restaurant_agent.settings import Settings


def test_amap_config_builds_url_and_bearer_headers() -> None:
    config = AmapMCPConfig(
        url="https://mcp.amap.com/mcp",
        api_key="test-key",
        bearer_token="test-token",
    )

    assert config.resolved_url == "https://mcp.amap.com/mcp?key=test-key"
    assert config.headers == {"Authorization": "Bearer test-token"}


def test_amap_config_does_not_duplicate_key_query_parameter() -> None:
    config = AmapMCPConfig(
        url="https://mcp.amap.com/mcp?key=existing-key",
        api_key="ignored-key",
    )

    assert config.resolved_url == "https://mcp.amap.com/mcp?key=existing-key"


def test_create_server_returns_none_without_url() -> None:
    assert create_amap_mcp_server(AmapMCPConfig()) is None


def test_default_service_mounts_configured_amap_server() -> None:
    service = create_default_agent_service(
        Settings(
            amap_mcp_url="https://mcp.amap.com/mcp",
            amap_mcp_key="test-key",
        )
    )

    assert service.mcp_server is not None
    assert len(service.agent.mcp_servers) == 1


@pytest.mark.asyncio
async def test_agent_enters_and_exits_mcp_server_for_a_run() -> None:
    class FakeMCPServer:
        def __init__(self) -> None:
            self.entered = False
            self.exited = False

        async def __aenter__(self):
            self.entered = True
            return self

        async def __aexit__(self, *args):
            self.exited = True

    mcp_server = FakeMCPServer()

    async def fake_runner(*args, **kwargs):
        assert mcp_server.entered is True
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="MCP is available.",
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
        mcp_server=mcp_server,
    )

    response = await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="Find a restaurant",
        )
    )

    assert response.message == "MCP is available."
    assert mcp_server.exited is True
