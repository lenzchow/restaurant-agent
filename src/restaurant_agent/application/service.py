from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, Runner, function_tool

from restaurant_agent.application.confirmation import ConfirmationManager
from restaurant_agent.domain.contracts import (
    ChatRequest,
    ChatResponse,
    ConfirmationDecision,
    Restaurant,
    RestaurantSearchInput,
    ResponseStatus,
)
from restaurant_agent.infrastructure.providers import RestaurantSearchProvider
from restaurant_agent.intents.classifier import IntentRecognizer, KeywordIntentRecognizer
from restaurant_agent.intents.models import IntentResult, IntentType


RunnerCallable = Callable[..., Awaitable[Any]]


class RestaurantAgentService:
    def __init__(
        self,
        provider: RestaurantSearchProvider,
        *,
        model: str | None = None,
        runner: RunnerCallable = Runner.run,
        mcp_server: Any | None = None,
        intent_recognizer: IntentRecognizer | None = None,
        amap_client: Any | None = None,
        dianping_provider: Any | None = None,
        route_enrichment: Any | None = None,
        confirmation_manager: ConfirmationManager | None = None,
    ) -> None:
        self.provider = provider
        self.runner = runner
        self.mcp_server = mcp_server
        self.intent_recognizer = intent_recognizer or KeywordIntentRecognizer()
        self.amap_client = amap_client
        self.dianping_provider = dianping_provider
        self.route_enrichment = route_enrichment
        self.confirmation_manager = confirmation_manager or ConfirmationManager()
        self.agent = Agent(
            name="Restaurant finder",
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            instructions=(
                "You help users find restaurants. The request includes a preliminary "
                "intent classification. Use it as routing context, but follow the "
                "user's actual request. For restaurant recommendation, extract search "
                "filters and call search_restaurants when useful. For dish recommendation, "
                "cuisine query, explain when the required live data "
                "source is unavailable instead of inventing results. Return a clear "
                "summary as a structured ChatResponse. "
                "When an Amap MCP server is available, use it for place lookup and "
                "route information. Never claim live availability or current opening "
                "status from sample data, and never invent route results."
            ),
            tools=[
                function_tool(self.search_restaurants),
                function_tool(self.get_restaurant_details),
            ],
            mcp_servers=[mcp_server] if mcp_server is not None else [],
            output_type=ChatResponse,
        )

    async def search_restaurants(
        self, request: RestaurantSearchInput, *, origin: str | None = None
    ) -> list[Restaurant]:
        if self.dianping_provider is not None:
            restaurants = await self.dianping_provider.search_restaurants(request)
            if origin and self.route_enrichment:
                return await self.route_enrichment.enrich(
                    restaurants, origin=origin, city=request.city
                )
            return restaurants
        return self.provider.search(request)

    async def get_restaurant_details(
        self,
        url_or_name: str,
        *,
        city: str | None = None,
        origin: str | None = None,
    ) -> Restaurant:
        if self.dianping_provider is None:
            raise RuntimeError("Dianping browser provider is not configured")
        restaurant = await self.dianping_provider.get_restaurant_details(url_or_name, city=city)
        if origin and self.route_enrichment:
            restaurant = (await self.route_enrichment.enrich([restaurant], origin=origin, city=city))[0]
        return restaurant

    async def enrich_restaurant_routes(
        self,
        restaurants: list[Restaurant],
        *,
        origin: str,
        city: str | None = None,
    ) -> list[Restaurant]:
        if self.route_enrichment is None:
            raise RuntimeError("Amap route enrichment is not configured")
        return await self.route_enrichment.enrich(restaurants, origin=origin, city=city)

    def analyze_request(self, request: ChatRequest) -> IntentResult:
        return self.intent_recognizer.recognize(request.message)

    async def answer(self, request: ChatRequest) -> ChatResponse:
        decision = request.confirmation or self._text_decision(request.message)
        if decision is ConfirmationDecision.REJECT:
            operation = self.confirmation_manager.reject(
                request.conversation_id, request.user_id
            )
            return ChatResponse(
                conversation_id=request.conversation_id,
                message="已取消本次大众点评浏览操作。",
                status=ResponseStatus.REJECTED,
                operation_id=operation.operation_id if operation else None,
            )
        if decision is ConfirmationDecision.APPROVE:
            operation = self.confirmation_manager.approve(
                request.conversation_id, request.user_id
            )
            if operation is not None:
                request = operation.request

        intent = self.analyze_request(request)
        if intent.missing_fields or intent.conflicts:
            return ChatResponse(
                conversation_id=request.conversation_id,
                message=intent.clarifying_question or "请补充必要条件。",
                intent=intent.intent,
                intents=intent.intents,
                missing_fields=intent.missing_fields,
                clarifying_question=intent.clarifying_question,
                conflicts=intent.conflicts,
            )
        if decision is not ConfirmationDecision.APPROVE and self._needs_dianping_confirmation(intent):
            operation = self.confirmation_manager.create(
                request,
                actions=[
                    "打开 Chrome",
                    "访问大众点评",
                    "读取餐厅推荐菜、营业时间、评分和评价",
                ],
            )
            return ChatResponse(
                conversation_id=request.conversation_id,
                message="本次请求需要打开 Chrome 并读取大众点评信息，是否继续？",
                status=ResponseStatus.CONFIRMATION_REQUIRED,
                operation_id=operation.operation_id,
                requires_confirmation=True,
                requested_actions=operation.actions,
                intent=intent.intent,
                intents=intent.intents,
            )
        return await self._execute(request, intent)

    async def _execute(
        self, request: ChatRequest, intent: IntentResult
    ) -> ChatResponse:
        route = None
        if (
            self.amap_client is not None
            and intent.route_origin
            and intent.route_destination
            and IntentType.ROUTE_QUERY in intent.intents
        ):
            route = await self.amap_client.route_between(
                intent.route_origin,
                intent.route_destination,
            )
        if self.mcp_server is None:
            result = await self._run(request, intent.model_dump(), route)
        else:
            async with self.mcp_server:
                result = await self._run(request, intent.model_dump(), route)
        output = result.final_output
        if isinstance(output, ChatResponse):
            updates = {"intent": output.intent or intent.intent}
            if not output.intents:
                updates["intents"] = intent.intents
            if output.route is None and route is not None:
                updates["route"] = route
            return output.model_copy(update=updates)
        return ChatResponse(
            conversation_id=request.conversation_id,
            message=str(output),
            intent=intent.intent,
            intents=intent.intents,
            route=route,
        )

    @staticmethod
    def _text_decision(message: str) -> ConfirmationDecision | None:
        normalized = message.strip().casefold()
        if normalized in {"确认", "继续", "开始", "同意", "yes", "y"}:
            return ConfirmationDecision.APPROVE
        if normalized in {"取消", "拒绝", "不要", "否", "no", "n"}:
            return ConfirmationDecision.REJECT
        return None

    def _needs_dianping_confirmation(self, intent: IntentResult) -> bool:
        if self.dianping_provider is None:
            return False
        live_intents = {
            IntentType.RESTAURANT_RECOMMENDATION,
            IntentType.DISH_RECOMMENDATION,
            IntentType.CUISINE_QUERY,
            IntentType.OPENING_HOURS_QUERY,
            IntentType.RATING_REVIEW_QUERY,
        }
        return bool(live_intents.intersection(intent.intents))

    async def _run(
        self,
        request: ChatRequest,
        intent: dict[str, Any],
        route: Any | None = None,
    ) -> Any:
        payload = request.model_dump()
        payload["recognized_intent"] = intent
        if route is not None:
            payload["route_context"] = route.model_dump()
        return await self.runner(
            self.agent,
            json.dumps(payload, ensure_ascii=False),
            conversation_id=request.conversation_id,
        )
