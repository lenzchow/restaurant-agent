from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from restaurant_agent.application.agent_planning import AgentParameterExtractor
from restaurant_agent.domain.contracts import RestaurantSearchInput


class SearchConditionStatus(StrEnum):
    NEEDS_CLARIFICATION = "needs_clarification"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"


class SearchConditionUpdate(BaseModel):
    status: SearchConditionStatus
    current_conditions: RestaurantSearchInput
    candidates: dict[str, list[str]] = Field(default_factory=dict)
    clarifying_question: str | None = None


class SearchConditionManager:
    """Maintains lightweight, in-memory search conditions per conversation."""

    _ambiguous_budget_terms = ("不要太贵", "别太贵", "便宜点", "实惠点")
    _ambiguous_distance_terms = ("离我近", "近一点", "附近")

    def __init__(self, extractor: AgentParameterExtractor) -> None:
        self.extractor = extractor
        self._conditions: dict[str, RestaurantSearchInput] = {}
        self._messages: dict[str, str] = {}

    def update(
        self, message: str, *, conversation_id: str = "__default__"
    ) -> SearchConditionUpdate:
        extraction = self.extractor.extract(message)
        current = self._conditions.get(conversation_id, RestaurantSearchInput())
        merged = self._merge(current, extraction.search_request, message)
        self._conditions[conversation_id] = merged
        self._messages[conversation_id] = message

        candidates = self._candidates(message)
        if candidates:
            return SearchConditionUpdate(
                status=SearchConditionStatus.NEEDS_CLARIFICATION,
                current_conditions=merged,
                candidates=candidates,
                clarifying_question=self._candidate_question(candidates),
            )
        return SearchConditionUpdate(
            status=SearchConditionStatus.NEEDS_CONFIRMATION,
            current_conditions=merged,
            clarifying_question=self.preview(merged),
        )

    def confirm(
        self, *, conversation_id: str = "__default__"
    ) -> RestaurantSearchInput | None:
        confirmed = self._conditions.pop(conversation_id, None)
        self._messages.pop(conversation_id, None)
        return confirmed

    def pending_message(self, *, conversation_id: str = "__default__") -> str | None:
        return self._messages.get(conversation_id)

    def has_pending(self, *, conversation_id: str = "__default__") -> bool:
        return conversation_id in self._conditions

    def clear(self, *, conversation_id: str = "__default__") -> None:
        self._conditions.pop(conversation_id, None)
        self._messages.pop(conversation_id, None)

    @staticmethod
    def preview(conditions: RestaurantSearchInput) -> str:
        labels = (
            ("地区", conditions.city),
            ("城区", conditions.location),
            ("菜系", conditions.cuisine),
            ("人均", f"{conditions.max_budget:g}元以内" if conditions.max_budget is not None else None),
            (
                "距离",
                f"{conditions.max_distance_km:g}km以内"
                if conditions.max_distance_km is not None
                else None,
            ),
            ("排序", conditions.sort if conditions.sort != "smart" else None),
            ("人数", f"{conditions.party_size}人" if conditions.party_size else None),
        )
        lines = [f"{label}：{value}" for label, value in labels if value]
        body = "\n".join(lines) if lines else "暂无明确筛选条件"
        return f"当前搜索条件为：\n{body}\n是否按以上条件搜索？"

    @classmethod
    def _candidates(cls, message: str) -> dict[str, list[str]]:
        candidates: dict[str, list[str]] = {}
        if any(term in message for term in cls._ambiguous_budget_terms):
            candidates["max_budget"] = ["100", "200"]
        if any(term in message for term in cls._ambiguous_distance_terms):
            candidates["max_distance_km"] = ["3", "5", "10"]
        return candidates

    @staticmethod
    def _candidate_question(candidates: dict[str, list[str]]) -> str:
        labels = {"max_budget": "人均预算", "max_distance_km": "距离"}
        choices = []
        for field, values in candidates.items():
            label = labels.get(field, field)
            choices.append(f"{label}可以选择：" + "、".join(str(value) for value in values))
        return "请从以下候选条件中选择：" + "；".join(choices) + "。"

    @staticmethod
    def _merge(
        previous: RestaurantSearchInput,
        current: RestaurantSearchInput,
        message: str,
    ) -> RestaurantSearchInput:
        updates = {
            field: getattr(current, field)
            for field in current.model_fields_set
            if field != "sort" or getattr(current, field) != "smart"
        }
        normalized = message.replace(" ", "")
        if any(term in normalized for term in ("预算不限", "人均不限", "不限预算")):
            updates["max_budget"] = None
        if any(term in normalized for term in ("距离不限", "不限距离")):
            updates["max_distance_km"] = None
        if any(term in normalized for term in ("菜系不限", "不限菜系")):
            updates["cuisine"] = None
        if any(term in normalized for term in ("地区不限", "地点不限", "不限地区", "不限地点")):
            updates["location"] = None
        return previous.model_copy(update=updates)
