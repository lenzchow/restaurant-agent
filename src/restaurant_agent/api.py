from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException

from restaurant_agent.application.service import RestaurantAgentService
from restaurant_agent.config.settings import Settings
from restaurant_agent.domain.contracts import ChatRequest, ChatResponse
from restaurant_agent.infrastructure.amap_mcp import (
    AmapMCPConfig,
    create_amap_mcp_server,
)
from restaurant_agent.infrastructure.amap_client import AmapMCPClient
from restaurant_agent.infrastructure.browser_harness import SubprocessBrowserHarness
from restaurant_agent.infrastructure.dianping_provider import DianpingBrowserProvider
from restaurant_agent.application.route_enrichment import RouteEnrichmentService
from restaurant_agent.infrastructure.providers import SampleRestaurantProvider

logger = logging.getLogger(__name__)


def create_default_agent_service(settings: Settings) -> RestaurantAgentService:
    amap_mcp_server = create_amap_mcp_server(
        AmapMCPConfig(
            url=settings.amap_mcp_url,
            api_key=settings.amap_mcp_key,
            bearer_token=settings.mcp_bearer_token,
        )
    )
    amap_client = AmapMCPClient(amap_mcp_server) if amap_mcp_server else None
    dianping_provider = None
    if settings.restaurant_provider.casefold() == "dianping":
        dianping_provider = DianpingBrowserProvider(
            SubprocessBrowserHarness(executable=settings.browser_harness_executable)
        )
    return RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        model=settings.openai_model,
        mcp_server=amap_mcp_server,
        amap_client=amap_client,
        dianping_provider=dianping_provider,
        route_enrichment=RouteEnrichmentService(amap_client) if amap_client else None,
    )


def create_app(service: Any | None = None) -> FastAPI:
    settings = Settings()
    agent_service = service or create_default_agent_service(settings)
    app = FastAPI(title="Restaurant Agent API", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            return await agent_service.answer(request)
        except Exception as exc:
            logger.exception("Restaurant agent request failed")
            raise HTTPException(
                status_code=500,
                detail="restaurant agent is temporarily unavailable",
            ) from exc

    return app


app = create_app()
