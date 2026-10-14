from __future__ import annotations

import re
from typing import Protocol

from restaurant_agent.intents.models import IntentResult, IntentType


class IntentRecognizer(Protocol):
    def recognize(self, message: str) -> IntentResult:
        ...


class KeywordIntentRecognizer:
    """Small deterministic recognizer used before an LLM or live data call."""

    _cuisine_terms = ("哪些菜系", "什么菜系", "有哪些菜系", "菜系")
    _dish_terms = ("推荐菜", "招牌菜", "必点", "菜品", "吃什么菜")
    _route_terms = (
        "路线",
        "怎么去",
        "打车",
        "公交",
        "地铁",
        "驾车",
        "开车多久",
        "过去要多久",
    )
    _details_terms = ("餐厅详情", "店铺详情", "详细信息", "地址电话")
    _hours_terms = ("营业时间", "几点开门", "几点关门", "几点营业", "营业到几点")
    _rating_terms = ("评分", "评价", "口碑", "好评", "几分")
    _review_summary_terms = ("评价总结", "评价汇总", "评论总结", "总结", "汇总")
    _restaurant_terms = (
        "餐厅",
        "饭店",
        "馆子",
        "吃饭",
        "晚餐",
        "午餐",
        "找一家",
        "查找",
        "找日料",
        "找火锅",
        "哪家",
        "美食",
        "筛选",
        "分类",
        "排序",
        "附近",
        "北京菜",
        "日料",
        "川菜",
        "粤菜",
        "东北菜",
        "火锅",
    )

    def recognize(self, message: str) -> IntentResult:
        text = message.strip().casefold()
        matches: list[tuple[IntentType, list[str]]] = []
        categories = (
            (IntentType.RESTAURANT_RECOMMENDATION, self._restaurant_terms),
            (IntentType.RESTAURANT_DETAILS_QUERY, self._details_terms),
            (IntentType.ROUTE_QUERY, self._route_terms),
            (IntentType.OPENING_HOURS_QUERY, self._hours_terms),
            (IntentType.RATING_REVIEW_QUERY, self._rating_terms),
            (IntentType.DISH_RECOMMENDATION, self._dish_terms),
            (IntentType.CUISINE_QUERY, self._cuisine_terms),
            (IntentType.REVIEW_SUMMARY_QUERY, self._review_summary_terms),
        )
        for intent, terms in categories:
            matched = self._find_terms(text, terms)
            if matched:
                matches.append((intent, matched))

        if not matches:
            return IntentResult(intent=IntentType.GENERAL_CHAT, confidence=0.5)

        intents = [intent for intent, _ in matches]
        primary_intent = intents[0]
        if IntentType.REVIEW_SUMMARY_QUERY in intents and any(
            term in text for term in ("总结", "汇总")
        ):
            primary_intent = IntentType.REVIEW_SUMMARY_QUERY
        elif IntentType.RESTAURANT_DETAILS_QUERY in intents and any(
            term in text for term in ("详情", "详细信息", "地址电话")
        ):
            primary_intent = IntentType.RESTAURANT_DETAILS_QUERY
        matched_terms = [term for _, terms in matches for term in terms]
        origin, destination = self._extract_route_points(message)
        missing_fields: list[str] = []
        if IntentType.ROUTE_QUERY in intents:
            if not origin:
                missing_fields.append("origin")
            if not destination:
                missing_fields.append("destination")

        conflicts = self._find_conflicts(text)
        question = None
        if missing_fields:
            question = "请提供路线的起点和终点。"
        elif conflicts:
            question = "你的条件存在冲突，请说明预算和餐厅档次哪个优先。"

        confidence = 0.98 if len(intents) == 1 else 0.9
        return IntentResult(
            intent=primary_intent,
            intents=intents,
            confidence=confidence,
            matched_terms=matched_terms,
            missing_fields=missing_fields,
            clarifying_question=question,
            conflicts=conflicts,
            route_origin=origin,
            route_destination=destination,
        )

    @staticmethod
    def _find_terms(text: str, terms: tuple[str, ...]) -> list[str]:
        return [term for term in terms if term.casefold() in text]

    @staticmethod
    def _extract_route_points(message: str) -> tuple[str | None, str | None]:
        match = re.search(r"从\s*(.+?)\s*到\s*(.+?)(?:[，。,.!?！？]|$)", message)
        if not match:
            return None, None
        destination = re.sub(
            r"(?:的)?(?:路线|交通|怎么去).*$", "", match.group(2).strip()
        ).strip()
        return match.group(1).strip(), destination

    @staticmethod
    def _find_conflicts(text: str) -> list[str]:
        maximum = re.search(r"不超过\s*(\d+(?:\.\d+)?)", text)
        minimum = re.search(r"至少\s*(\d+(?:\.\d+)?)", text)
        if maximum and minimum and float(minimum.group(1)) > float(maximum.group(1)):
            return ["minimum_budget_exceeds_maximum_budget"]
        return []
