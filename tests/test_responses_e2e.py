from __future__ import annotations

import os

import pytest
from agents import set_tracing_disabled

from restaurant_agent.application.service import RestaurantAgentService
from restaurant_agent.config.settings import Settings
from restaurant_agent.domain.contracts import ChatRequest, ChatResponse
from restaurant_agent.infrastructure.providers import SampleRestaurantProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_responses_api_end_to_end() -> None:
    """Run the complete service path against the configured Responses API model."""

    if os.getenv("RUN_RESPONSES_E2E") != "1":
        pytest.skip("set RUN_RESPONSES_E2E=1 to call the configured Responses API")

    settings = Settings()
    if not settings.openai_api_key:
        pytest.skip("OPENAI_API_KEY is not configured")
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)
    if settings.openai_base_url:
        os.environ.setdefault("OPENAI_BASE_URL", settings.openai_base_url)
    set_tracing_disabled(True)

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        model=settings.openai_model,
    )
    response = await service.answer(
        ChatRequest(
            conversation_id="responses-e2e",
            user_id="responses-e2e-user",
            message="在北京推荐一家日料餐厅，给我简短说明。",
        )
    )

    assert isinstance(response, ChatResponse)
    assert response.message.strip()
