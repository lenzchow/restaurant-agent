from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import HTMLResponse

from restaurant_agent.adapters.feishu import FeishuAdapter, FeishuClient


def create_platform_router(
    service: Any, feishu_client: FeishuClient | None = None
) -> APIRouter:
    router = APIRouter()
    page = (Path(__file__).parent / "templates" / "chat.html").read_text()

    @router.get("/chat", response_class=HTMLResponse)
    async def chat_page() -> HTMLResponse:
        return HTMLResponse(page)

    @router.post("/webhooks/feishu")
    async def feishu_webhook(
        event: dict[str, Any], background_tasks: BackgroundTasks
    ) -> dict[str, Any]:
        challenge = FeishuAdapter.challenge(event)
        if challenge is not None:
            return challenge
        request = FeishuAdapter.to_chat_request(event)
        message_id = FeishuAdapter.message_id(event)
        if feishu_client is not None and message_id is not None:
            async def process_message() -> None:
                response = await service.answer(request)
                message = FeishuAdapter.to_message(response)
                await feishu_client.reply_text(
                    message_id, message["content"]["text"]
                )

            background_tasks.add_task(
                process_message,
            )
            return {"ok": True}
        response = await service.answer(request)
        message = FeishuAdapter.to_message(response)
        return message

    return router
