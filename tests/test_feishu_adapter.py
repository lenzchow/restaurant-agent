import json

import pytest

from restaurant_agent.adapters.feishu import FeishuAdapter, FeishuClient
from restaurant_agent.domain.contracts import ChatResponse, RestaurantSearchInput


def test_feishu_adapter_converts_text_event_to_chat_request() -> None:
    request = FeishuAdapter.to_chat_request(
        {
            "event": {
                "message": {
                    "message_id": "om_123",
                    "chat_id": "oc_123",
                    "message_type": "text",
                    "content": '{"text":"在北京找日料"}',
                },
                "sender": {"sender_id": {"open_id": "ou_123"}},
            }
        }
    )

    assert request.conversation_id == "oc_123"
    assert request.user_id == "ou_123"
    assert request.message == "在北京找日料"
    assert request.platform == "feishu"


def test_feishu_adapter_formats_condition_preview_as_text_message() -> None:
    response = ChatResponse(
        conversation_id="oc_123",
        message="当前搜索条件为：",
        search_conditions=RestaurantSearchInput(city="北京", cuisine="日料"),
        search_confirmation_required=True,
    )

    payload = FeishuAdapter.to_message(response)

    assert payload["msg_type"] == "text"
    assert "北京" in payload["content"]["text"]


def test_feishu_challenge_is_returned_without_running_agent() -> None:
    assert FeishuAdapter.challenge({"challenge": "challenge-value"}) == {
        "challenge": "challenge-value"
    }


@pytest.mark.asyncio
async def test_feishu_client_replies_to_message_with_tenant_token() -> None:
    calls: list[tuple[str, str, dict]] = []

    async def fake_request(method: str, url: str, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("tenant_access_token/internal"):
            return {"tenant_access_token": "tenant-token"}
        return {"code": 0}

    client = FeishuClient(
        app_id="app-id",
        app_secret="app-secret",
        request=fake_request,
    )

    await client.reply_text("om_123", "已收到")

    assert calls[0][1].endswith("tenant_access_token/internal")
    assert calls[1][0] == "POST"
    assert calls[1][1].endswith("im/v1/messages/om_123/reply")
    assert calls[1][2]["headers"]["Authorization"] == "Bearer tenant-token"
    assert json.loads(calls[1][2]["json"]["content"]) == {"text": "已收到"}
