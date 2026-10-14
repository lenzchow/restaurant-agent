from fastapi.testclient import TestClient

from restaurant_agent.api import create_app
from restaurant_agent.domain.contracts import ChatResponse


class FakeService:
    async def answer(self, request):
        return ChatResponse(
            conversation_id=request.conversation_id,
            message=f"收到：{request.message}",
        )


def test_web_page_is_available() -> None:
    client = TestClient(create_app(FakeService()))

    response = client.get("/chat")

    assert response.status_code == 200
    assert "Restaurant Agent" in response.text


def test_feishu_webhook_reuses_agent_service() -> None:
    client = TestClient(create_app(FakeService()))

    response = client.post(
        "/webhooks/feishu",
        json={
            "event": {
                "message": {
                    "chat_id": "oc_123",
                    "message_type": "text",
                    "content": '{"text":"找一家日料"}',
                },
                "sender": {"sender_id": {"open_id": "ou_123"}},
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["msg_type"] == "text"
    assert "找一家日料" in response.json()["content"]["text"]
