from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

from agents import Agent, Runner, SQLiteSession, function_tool

from restaurant_agent.application.agent_planning import (
    AgentParameterExtractor,
    ToolRouter,
)
from restaurant_agent.application.confirmation import ConfirmationManager
from restaurant_agent.application.guardrails import (
    restaurant_input_guardrail,
    restaurant_output_guardrail,
)
from restaurant_agent.application.search_state import SearchConditionManager
from restaurant_agent.domain.contracts import (
    ChatRequest,
    ChatResponse,
    ConfirmationDecision,
    Restaurant,
    RestaurantSearchInput,
    ResponseStatus,
    RouteInfo,
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
        parameter_extractor: AgentParameterExtractor | None = None,
        tool_router: ToolRouter | None = None,
        search_condition_manager: SearchConditionManager | None = None,
        session_db_path: str | None = None,
    ) -> None:
        self.provider = provider
        self.runner = runner
        self.mcp_server = mcp_server
        self.intent_recognizer = intent_recognizer or KeywordIntentRecognizer()
        self.amap_client = amap_client
        self.dianping_provider = dianping_provider
        self.route_enrichment = route_enrichment
        self.confirmation_manager = confirmation_manager or ConfirmationManager()
        self.parameter_extractor = parameter_extractor or AgentParameterExtractor()
        self.tool_router = tool_router or ToolRouter()
        self.search_condition_manager = search_condition_manager or SearchConditionManager(
            self.parameter_extractor
        )
        self.session_db_path = session_db_path or os.getenv(
            "AGENT_SESSION_DB_PATH", ":memory:"
        )
        self._sessions: dict[str, SQLiteSession] = {}
        self._workflow_context: dict[str, dict[str, Any]] = {}
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
                "The request includes an agent_plan with structured parameters and ordered "
                "actions and a workflow with dependencies; execute the workflow steps in "
                "order and complete all applicable actions. "
                "When returning recommended dishes, preserve the image URLs in "
                "recommendations[].recommended_dish_images or explain that the page did "
                "not provide images; never invent image URLs. "
                "When an Amap MCP server is available, use it for place lookup and "
                "route information. Never claim live availability or current opening "
                "status from sample data, and never invent route results."
            ),
            tools=[
                function_tool(self.search_restaurants),
                function_tool(self.get_restaurant_details),
                function_tool(self.get_recommended_dishes),
                function_tool(self.get_review_summary),
                function_tool(self.get_full_reviews),
                function_tool(self.query_route),
            ],
            input_guardrails=[restaurant_input_guardrail],
            output_guardrails=[restaurant_output_guardrail],
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

    async def get_restaurant_details_batch(
        self,
        urls_or_names: list[str],
        *,
        city: str | None = None,
        origin: str | None = None,
    ) -> list[Restaurant]:
        async def load_one(value: str) -> Restaurant:
            try:
                return await self.get_restaurant_details(
                    value, city=city, origin=origin
                )
            except Exception as exc:
                return Restaurant(
                    name=value,
                    cuisine="未知",
                    address="未获取到地址",
                    price_per_person=0,
                    distance_km=0,
                    route_error=str(exc),
                    data_source="dianping",
                    data_source_status="error",
                )

        return list(await asyncio.gather(*(load_one(value) for value in urls_or_names[:10])))

    async def get_recommended_dishes(
        self, url_or_name: str, *, city: str | None = None
    ) -> dict[str, Any]:
        restaurant = await self.get_restaurant_details(url_or_name, city=city)
        return {
            "dishes": restaurant.recommended_dishes,
            "images": restaurant.recommended_dish_images,
            "image_note": restaurant.recommendation_image_note
            or (
                "页面未抓取到推荐菜图片。"
                if restaurant.recommended_dishes
                and not restaurant.recommended_dish_images
                else None
            ),
        }

    async def get_review_summary(
        self, url_or_name: str, *, city: str | None = None
    ) -> dict[str, Any]:
        restaurant = await self.get_restaurant_details(url_or_name, city=city)
        return {
            "restaurant": restaurant.name,
            "rating": restaurant.rating,
            "summary": restaurant.review_summary,
            "highlights": restaurant.review_highlights,
            "review_count": restaurant.review_count,
            "review_tags": restaurant.review_tags,
            "follow_up": "是否需要查看抓取评价内容的完整信息？",
        }

    async def get_full_reviews(
        self, url_or_name: str, *, city: str | None = None
    ) -> dict[str, Any]:
        restaurant = await self.get_restaurant_details(url_or_name, city=city)
        return {
            "restaurant": restaurant.name,
            "review_count": restaurant.review_count,
            "review_tags": restaurant.review_tags,
            "reviews": [review.model_dump() for review in restaurant.reviews],
        }

    async def query_route(
        self,
        origin: str,
        destination: str,
        *,
        city: str | None = None,
        modes: list[str] | None = None,
    ) -> RouteInfo:
        if self.amap_client is None:
            raise RuntimeError("Amap route tool is not configured")
        requested_modes = list(dict.fromkeys(modes or ["driving", "taxi", "bus", "subway"]))
        supported_modes = {"driving", "taxi", "bus", "subway"}
        route = await self.amap_client.route_between(origin, destination, city=city)
        return route.model_copy(
            update={
                "requested_modes": requested_modes,
                "unsupported_modes": [
                    mode for mode in requested_modes if mode not in supported_modes
                ],
            }
        )

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
        condition_confirmed = False
        browser_operation_approved = False
        if decision is ConfirmationDecision.REJECT:
            if self.search_condition_manager.has_pending(
                conversation_id=request.conversation_id
            ):
                self.search_condition_manager.clear(
                    conversation_id=request.conversation_id
                )
                return ChatResponse(
                    conversation_id=request.conversation_id,
                    message="已取消本次搜索。",
                    status=ResponseStatus.REJECTED,
                )
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
            pending_message = self.search_condition_manager.pending_message(
                conversation_id=request.conversation_id
            )
            confirmed_conditions = self.search_condition_manager.confirm(
                conversation_id=request.conversation_id
            )
            if confirmed_conditions is not None:
                condition_confirmed = True
                decision = None
                request = request.model_copy(
                    update={
                        "message": pending_message or request.message,
                        "confirmation": None,
                    }
                )
            operation = self.confirmation_manager.approve(
                request.conversation_id, request.user_id
            )
            if operation is not None:
                browser_operation_approved = True
                request = operation.request

        extraction = self.parameter_extractor.extract(request.message)
        search_request = extraction.search_request
        intent = self.analyze_request(request)
        if (
            intent.intent is IntentType.GENERAL_CHAT
            and search_request.model_fields_set
        ):
            intent = intent.model_copy(
                update={
                    "intent": IntentType.RESTAURANT_RECOMMENDATION,
                    "intents": [IntentType.RESTAURANT_RECOMMENDATION],
                    "confidence": 0.8,
                }
            )
        if self._needs_route_scope_question(request.message, intent, search_request):
            return ChatResponse(
                conversation_id=request.conversation_id,
                message="路线查询范围需要确认：是查询全部餐厅，还是指定一家餐厅？",
                intent=intent.intent,
                intents=intent.intents,
                clarifying_question="请回复‘全部餐厅’或指定餐厅名称。",
            )
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
        if (
            not condition_confirmed
            and not browser_operation_approved
            and self.dianping_provider is not None
            and IntentType.RESTAURANT_RECOMMENDATION in intent.intents
        ):
            condition_update = self.search_condition_manager.update(
                request.message,
                conversation_id=request.conversation_id,
            )
            return ChatResponse(
                conversation_id=request.conversation_id,
                message=condition_update.clarifying_question
                or "请确认当前搜索条件。",
                status=ResponseStatus.CONFIRMATION_REQUIRED,
                requires_confirmation=True,
                requested_actions=["确认当前搜索条件"],
                intent=intent.intent,
                intents=intent.intents,
                search_conditions=condition_update.current_conditions,
                condition_candidates=condition_update.candidates,
                search_confirmation_required=True,
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
        return await self._execute(
            request,
            intent,
            search_request=search_request,
            restaurant_name=extraction.restaurant_name,
            restaurant_url=extraction.restaurant_url,
            route_modes=extraction.route_modes,
        )

    async def _execute(
        self,
        request: ChatRequest,
        intent: IntentResult,
        *,
        search_request: RestaurantSearchInput | None = None,
        restaurant_name: str | None = None,
        restaurant_url: str | None = None,
        route_modes: list[str] | None = None,
    ) -> ChatResponse:
        route = None
        if (
            self.amap_client is not None
            and intent.route_origin
            and intent.route_destination
            and IntentType.ROUTE_QUERY in intent.intents
        ):
            route = await self.query_route(
                intent.route_origin,
                intent.route_destination,
                modes=route_modes,
            )
        if self.mcp_server is None:
            result = await self._run(
                request,
                intent.model_dump(),
                route,
                search_request=search_request,
                restaurant_name=restaurant_name,
                restaurant_url=restaurant_url,
                route_modes=route_modes,
            )
        else:
            async with self.mcp_server:
                result = await self._run(
                    request,
                    intent.model_dump(),
                    route,
                    search_request=search_request,
                    restaurant_name=restaurant_name,
                    restaurant_url=restaurant_url,
                    route_modes=route_modes,
                )
        output = result.final_output
        if isinstance(output, ChatResponse):
            updates = {"intent": output.intent or intent.intent}
            if not output.intents:
                updates["intents"] = intent.intents
            if output.route is None and route is not None:
                updates["route"] = route
            response = output.model_copy(update=updates)
        else:
            response = ChatResponse(
                conversation_id=request.conversation_id,
                message=str(output),
                intent=intent.intent,
                intents=intent.intents,
                route=route,
            )
        self._workflow_context[request.conversation_id] = {
            "intent": intent.model_dump(),
            "search_request": search_request.model_dump() if search_request else None,
            "route": route.model_dump() if route else None,
            "recommendations": [item.model_dump() for item in response.recommendations],
        }
        return response

    def get_workflow_context(self, conversation_id: str) -> dict[str, Any]:
        return dict(self._workflow_context.get(conversation_id, {}))

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
            IntentType.RESTAURANT_DETAILS_QUERY,
            IntentType.DISH_RECOMMENDATION,
            IntentType.CUISINE_QUERY,
            IntentType.OPENING_HOURS_QUERY,
            IntentType.RATING_REVIEW_QUERY,
            IntentType.REVIEW_SUMMARY_QUERY,
        }
        return bool(live_intents.intersection(intent.intents))

    @staticmethod
    def _needs_route_scope_question(
        message: str,
        intent: IntentResult,
        search_request: RestaurantSearchInput,
    ) -> bool:
        if not {
            IntentType.ROUTE_QUERY,
            IntentType.RESTAURANT_RECOMMENDATION,
        }.issubset(set(intent.intents)):
            return False
        normalized = message.casefold()
        multi = any(term in normalized for term in ("全部", "所有", "每家"))
        return multi or (search_request.limit > 1 and "路线" in normalized)

    async def _run(
        self,
        request: ChatRequest,
        intent: dict[str, Any],
        route: Any | None = None,
        *,
        search_request: RestaurantSearchInput | None = None,
        restaurant_name: str | None = None,
        restaurant_url: str | None = None,
        route_modes: list[str] | None = None,
    ) -> Any:
        payload = request.model_dump()
        payload["recognized_intent"] = intent
        intent_result = IntentResult.model_validate(intent)
        workflow = self.tool_router.workflow(intent_result, route_modes=route_modes)
        payload["agent_plan"] = {
            "actions": [action.value for action in self.tool_router.plan(intent_result)],
            "workflow": workflow.model_dump(),
            "route_origin": intent.get("route_origin"),
            "route_destination": intent.get("route_destination"),
            "restaurant_name": restaurant_name,
            "restaurant_url": restaurant_url,
            "search_request": (
                search_request.model_dump() if search_request is not None else None
            ),
        }
        if route is not None:
            payload["route_context"] = route.model_dump()
        session = self._sessions.setdefault(
            request.conversation_id,
            SQLiteSession(request.conversation_id, db_path=self.session_db_path),
        )
        return await self.runner(
            self.agent,
            json.dumps(payload, ensure_ascii=False),
            session=session,
        )
