from __future__ import annotations

import re
from enum import StrEnum

from pydantic import BaseModel, Field

from restaurant_agent.domain.contracts import RestaurantSearchInput
from restaurant_agent.intents.models import IntentResult, IntentType


class AgentAction(StrEnum):
    SEARCH_RESTAURANTS = "search_restaurants"
    GET_RESTAURANT_DETAILS = "get_restaurant_details"
    QUERY_ROUTE = "query_route"
    QUERY_CUISINES = "query_cuisines"


class WorkflowStepType(StrEnum):
    SEARCH_RESTAURANTS = "search_restaurants"
    GET_RESTAURANT_DETAILS = "get_restaurant_details"
    GET_RECOMMENDED_DISHES = "get_recommended_dishes"
    GET_REVIEWS = "get_reviews"
    SUMMARIZE_REVIEWS = "summarize_reviews"
    QUERY_ROUTE = "query_route"
    QUERY_CUISINES = "query_cuisines"
    COMPOSE_RESPONSE = "compose_response"


class WorkflowStep(BaseModel):
    id: str
    type: WorkflowStepType
    depends_on: list[str] = Field(default_factory=list)


class WorkflowPlan(BaseModel):
    steps: list[WorkflowStep]
    route_modes: list[str] = Field(default_factory=list)


class AgentParameterExtraction(BaseModel):
    search_request: RestaurantSearchInput = Field(default_factory=RestaurantSearchInput)
    restaurant_name: str | None = None
    restaurant_url: str | None = None
    route_origin: str | None = None
    route_destination: str | None = None
    route_modes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1, ge=0, le=1)
    unrecognized_fields: list[str] = Field(default_factory=list)


class AgentParameterExtractor:
    """Extracts stable business parameters before the LLM execution step."""

    _cuisines = (
        "日本菜", "日料", "川菜", "粤菜", "湘菜", "东北菜", "北京菜",
        "韩式料理", "火锅", "烧烤", "云南菜", "素食", "面馆", "咖啡",
    )
    _sorts = {
        "评价最多": "review_count",
        "好评": "rating",
        "人气": "popularity",
        "口味": "taste",
        "环境最佳": "environment",
        "服务最佳": "service",
        "预订优先": "booking",
        "人均最高": "price_high",
        "人均最低": "price_low",
    }

    def extract(self, message: str) -> AgentParameterExtraction:
        text = message.strip()
        values: dict[str, object] = {}
        city = self._city(text)
        location = None
        if city:
            after_city = text.split(city, 1)[1]
            location = self._first(after_city, r"([\u4e00-\u9fff]{2,8}区)")
        cuisine = next((item for item in self._cuisines if item in text), None)
        budget = self._number(text, r"人均\s*(?:不超过|不高于|低于|以内|以下)?\s*(\d+(?:\.\d+)?)")
        limit = self._number(text, r"(\d+)\s*(?:家|个|条)" )
        distance = self._number(text, r"距离\s*(\d+(?:\.\d+)?)\s*公里")
        party_size = self._number(text, r"(\d+)\s*个人")
        page = self._number(text, r"第\s*(\d+)\s*页")
        sort = next((value for label, value in self._sorts.items() if label in text), None)
        unrecognized_fields = []
        if any(term in text for term in ("环境好一些", "环境好点", "服务好一些", "服务好点")):
            unrecognized_fields.append("sort")
        if city:
            values["city"] = city
        if location:
            values["location"] = location
        if cuisine:
            values["cuisine"] = cuisine
        if budget is not None:
            values["max_budget"] = budget
        if limit is not None:
            values["limit"] = int(limit)
        if distance is not None:
            values["max_distance_km"] = distance
        if party_size is not None:
            values["party_size"] = int(party_size)
        if page is not None:
            values["page"] = int(page)
        if sort:
            values["sort"] = sort
        origin, destination = self._route_points(text)
        route_modes = self._route_modes(text)
        return AgentParameterExtraction(
            search_request=RestaurantSearchInput(**values),
            restaurant_name=None if self._restaurant_url(text) else self._restaurant_name(text),
            restaurant_url=self._restaurant_url(text),
            route_origin=origin,
            route_destination=destination,
            route_modes=route_modes,
            confidence=0.75 if unrecognized_fields else 1.0,
            unrecognized_fields=unrecognized_fields,
        )

    @staticmethod
    def _first(text: str, pattern: str) -> str | None:
        match = re.search(pattern, text)
        return match.group(1) if match else None

    @classmethod
    def _city(cls, text: str) -> str | None:
        match = re.search(r"在([\u4e00-\u9fff]{2,6}?)(?=[\u4e00-\u9fff]{2,8}区|附近|找)", text)
        return match.group(1) if match else None

    @staticmethod
    def _number(text: str, pattern: str) -> float | None:
        match = re.search(pattern, text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _route_points(text: str) -> tuple[str | None, str | None]:
        match = re.search(r"从\s*(.+?)\s*到\s*(.+?)(?:[，。,.!?！？]|$)", text)
        if not match:
            return None, None
        destination = re.sub(
            r"(?:的)?(?:路线|交通|怎么去)$", "", match.group(2).strip()
        ).strip()
        return match.group(1).strip(), destination

    @staticmethod
    def _route_modes(text: str) -> list[str]:
        terms = (
            ("驾车", "driving"),
            ("开车", "driving"),
            ("打车", "taxi"),
            ("公交", "bus"),
            ("地铁", "subway"),
            ("骑单车", "bicycle"),
            ("自行车", "bicycle"),
            ("骑摩托车", "motorcycle"),
            ("摩托车", "motorcycle"),
        )
        return list(dict.fromkeys(mode for label, mode in terms if label in text))

    @staticmethod
    def _restaurant_name(text: str) -> str | None:
        match = re.search(
            r"(?:查询|查看|查一下|介绍一下|评价一下|总结一下)\s*"
            r"(.+?)(?=(?:的)?(?:详细信息|推荐菜|招牌菜|评价|评论|营业时间|路线|怎么去)$)",
            text,
        )
        if not match:
            return None
        name = match.group(1).strip()
        return name or None

    @staticmethod
    def _restaurant_url(text: str) -> str | None:
        match = re.search(r"https?://(?:www\.)?dianping\.com/shop/[A-Za-z0-9_-]+", text)
        return match.group(0) if match else None


class ToolRouter:
    """Maps recognized intent combinations to an ordered tool plan."""

    def plan(self, intent: IntentResult) -> list[AgentAction]:
        intents = set(intent.intents or [intent.intent])
        actions: list[AgentAction] = []
        if IntentType.RESTAURANT_RECOMMENDATION in intents:
            actions.append(AgentAction.SEARCH_RESTAURANTS)
        if intents.intersection(
            {
                IntentType.RESTAURANT_DETAILS_QUERY,
                IntentType.DISH_RECOMMENDATION,
                IntentType.OPENING_HOURS_QUERY,
                IntentType.RATING_REVIEW_QUERY,
                IntentType.REVIEW_SUMMARY_QUERY,
            }
        ):
            actions.append(AgentAction.GET_RESTAURANT_DETAILS)
        if IntentType.CUISINE_QUERY in intents:
            actions.append(AgentAction.QUERY_CUISINES)
        if IntentType.ROUTE_QUERY in intents:
            actions.append(AgentAction.QUERY_ROUTE)
        return actions

    def workflow(
        self, intent: IntentResult, *, route_modes: list[str] | None = None
    ) -> WorkflowPlan:
        intents = set(intent.intents or [intent.intent])
        steps: list[WorkflowStep] = []

        def add(step_type: WorkflowStepType, depends_on: list[str] | None = None) -> None:
            steps.append(
                WorkflowStep(
                    id=f"{step_type.value}_{len(steps) + 1}",
                    type=step_type,
                    depends_on=depends_on or [],
                )
            )

        search_id: str | None = None
        detail_id: str | None = None
        if IntentType.RESTAURANT_RECOMMENDATION in intents:
            add(WorkflowStepType.SEARCH_RESTAURANTS)
            search_id = steps[-1].id
        if IntentType.RESTAURANT_DETAILS_QUERY in intents:
            add(WorkflowStepType.GET_RESTAURANT_DETAILS)
            detail_id = steps[-1].id
        if intents.intersection(
            {
                IntentType.DISH_RECOMMENDATION,
                IntentType.OPENING_HOURS_QUERY,
                IntentType.RATING_REVIEW_QUERY,
            }
        ):
            add(WorkflowStepType.GET_RESTAURANT_DETAILS, [search_id] if search_id else None)
            detail_id = steps[-1].id
        if IntentType.DISH_RECOMMENDATION in intents:
            add(WorkflowStepType.GET_RECOMMENDED_DISHES, [detail_id] if detail_id else None)
        if IntentType.REVIEW_SUMMARY_QUERY in intents:
            add(WorkflowStepType.GET_REVIEWS, [detail_id] if detail_id else None)
            reviews_id = steps[-1].id
            add(WorkflowStepType.SUMMARIZE_REVIEWS, [reviews_id])
        if IntentType.CUISINE_QUERY in intents:
            add(WorkflowStepType.QUERY_CUISINES)
        if IntentType.ROUTE_QUERY in intents:
            add(WorkflowStepType.QUERY_ROUTE, [search_id] if search_id else None)
        add(WorkflowStepType.COMPOSE_RESPONSE, [step.id for step in steps])
        return WorkflowPlan(steps=steps, route_modes=route_modes or [])
