from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from restaurant_agent.domain.contracts import ChatRequest, ChatResponse


RequestCallable = Callable[..., Awaitable[dict[str, Any]]]


class FeishuAdapter:
    """Converts Feishu webhook payloads to and from the common chat contract."""

    @staticmethod
    def challenge(event: dict[str, Any]) -> dict[str, Any] | None:
        challenge = event.get("challenge")
        return {"challenge": challenge} if challenge else None

    @staticmethod
    def to_chat_request(event: dict[str, Any]) -> ChatRequest:
        message = event.get("event", {}).get("message", {})
        sender = event.get("event", {}).get("sender", {})
        content = message.get("content", "")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                content = {"text": content}
        text = str(content.get("text", "")).strip()
        if not text:
            raise ValueError("Feishu event does not contain a text message")
        sender_id = sender.get("sender_id", {})
        user_id = str(sender_id.get("open_id") or sender_id.get("user_id") or "unknown")
        conversation_id = str(message.get("chat_id") or user_id)
        return ChatRequest(
            conversation_id=conversation_id,
            user_id=user_id,
            message=text,
            platform="feishu",
        )

    @staticmethod
    def message_id(event: dict[str, Any]) -> str | None:
        value = event.get("event", {}).get("message", {}).get("message_id")
        return str(value) if value else None

    @staticmethod
    def to_message(response: ChatResponse) -> dict[str, Any]:
        text = response.message
        if response.search_conditions is not None:
            conditions = response.search_conditions
            fields = (
                ("地区", conditions.city),
                ("城区", conditions.location),
                ("菜系", conditions.cuisine),
                (
                    "人均",
                    f"{conditions.max_budget:g}元以内"
                    if conditions.max_budget is not None
                    else None,
                ),
                (
                    "距离",
                    f"{conditions.max_distance_km:g}km以内"
                    if conditions.max_distance_km is not None
                    else None,
                ),
            )
            preview = "\n".join(f"{label}：{value}" for label, value in fields if value)
            if preview and preview not in text:
                text = f"{text}\n{preview}"
        candidates = response.condition_candidates.model_dump(exclude_defaults=True)
        if candidates:
            choices = "；".join(
                f"{field}: {', '.join(map(str, values))}"
                for field, values in candidates.items()
            )
            text = f"{text}\n可选条件：{choices}"
        return {"msg_type": "text", "content": {"text": text}}


class FeishuClient:
    """Minimal Feishu Open API client for replying to bot messages."""

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        base_url: str = "https://open.feishu.cn/open-apis",
        request: RequestCallable | None = None,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = base_url.rstrip("/")
        self._request = request or self._http_request

    async def reply_text(self, message_id: str, text: str) -> None:
        token_payload = await self._request(
            "POST",
            f"{self.base_url}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
        )
        token = token_payload.get("tenant_access_token")
        if not token:
            raise RuntimeError("Feishu did not return a tenant access token")
        result = await self._request(
            "POST",
            f"{self.base_url}/im/v1/messages/{message_id}/reply",
            headers={"Authorization": f"Bearer {token}"},
            json={"msg_type": "text", "content": json.dumps({"text": text}, ensure_ascii=False)},
        )
        if result.get("code", 0) != 0:
            raise RuntimeError(f"Feishu reply failed: {result}")

    @staticmethod
    async def _http_request(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            value = response.json()
            return value if isinstance(value, dict) else {}
