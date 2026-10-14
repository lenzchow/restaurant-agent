from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from restaurant_agent.api import create_app
from restaurant_agent.contracts import ChatResponse, ResponseStatus


class FakeService:
    async def answer(self, request):
        return ChatResponse(
            conversation_id=request.conversation_id,
            message="Here is a recommendation.",
            recommendations=[],
        )


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(FakeService())),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_endpoint_returns_platform_neutral_response(
    sample_request_payload: dict[str, str],
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(FakeService())),
        base_url="http://test",
    ) as client:
        response = await client.post("/v1/chat", json=sample_request_payload)

    assert response.status_code == 200
    assert response.json()["conversation_id"] == "conversation-test"
    assert response.json()["message"] == "Here is a recommendation."


@pytest.mark.asyncio
async def test_chat_endpoint_rejects_missing_message() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=create_app(FakeService())),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/chat",
            json={"conversation_id": "conversation-test", "user_id": "user-test"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_serializes_confirmation_contract() -> None:
    class ConfirmationService:
        async def answer(self, request):
            return ChatResponse(
                conversation_id=request.conversation_id,
                message="是否继续？",
                status=ResponseStatus.CONFIRMATION_REQUIRED,
                operation_id="operation-1",
                requires_confirmation=True,
                requested_actions=["打开 Chrome", "访问大众点评"],
            )

    async with AsyncClient(
        transport=ASGITransport(app=create_app(ConfirmationService())),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/chat",
            json={"user_id": "user-test", "message": "找一家餐厅"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "confirmation_required"
    assert response.json()["requires_confirmation"] is True
