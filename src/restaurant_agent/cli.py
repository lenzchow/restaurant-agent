from __future__ import annotations

import argparse
import asyncio
import uuid
from typing import Any

from restaurant_agent.domain.contracts import ChatRequest, ChatResponse


def format_cli_response(response: ChatResponse) -> str:
    text = response.message
    if response.search_conditions is not None:
        conditions = response.search_conditions
        values = (
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
        preview = "\n".join(f"{label}：{value}" for label, value in values if value)
        if preview and preview not in text:
            text = f"{text}\n{preview}"
    return text


async def run_cli(service: Any) -> None:
    conversation_id = str(uuid.uuid4())
    while True:
        message = input("你：").strip()
        if message.casefold() in {"退出", "exit", "quit"}:
            return
        if not message:
            continue
        response = await service.answer(
            ChatRequest(
                conversation_id=conversation_id,
                user_id="cli-user",
                message=message,
            )
        )
        print(f"Agent：{format_cli_response(response)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Restaurant Agent CLI")
    parser.parse_args()
    from restaurant_agent.api import create_default_agent_service
    from restaurant_agent.config.settings import Settings

    asyncio.run(run_cli(create_default_agent_service(Settings())))


if __name__ == "__main__":
    main()
