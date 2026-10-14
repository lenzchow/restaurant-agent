from __future__ import annotations

import pytest

from restaurant_agent.intents.classifier import KeywordIntentRecognizer
from restaurant_agent.intents.models import IntentType


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("帮我找一家适合晚餐的馆子", IntentType.RESTAURANT_RECOMMENDATION),
        ("我想找日料", IntentType.RESTAURANT_RECOMMENDATION),
        ("查询全聚德餐厅的详细信息", IntentType.RESTAURANT_DETAILS_QUERY),
        ("这家店有什么推荐菜？", IntentType.DISH_RECOMMENDATION),
        ("当前榜单上有哪些菜系？", IntentType.CUISINE_QUERY),
        ("帮我筛选北京菜，按好评排序", IntentType.RESTAURANT_RECOMMENDATION),
        ("帮我查从学校到这家店的路线", IntentType.ROUTE_QUERY),
        ("这家店几点关门？", IntentType.OPENING_HOURS_QUERY),
        ("这家店评分和评价怎么样？", IntentType.RATING_REVIEW_QUERY),
        ("请总结这家餐厅的评价", IntentType.REVIEW_SUMMARY_QUERY),
    ],
)
def test_keyword_recognizer_classifies_restaurant_intents(
    message: str, expected: IntentType
) -> None:
    result = KeywordIntentRecognizer().recognize(message)

    assert result.intent is expected


def test_keyword_recognizer_prefers_cuisine_query_over_ranking_context() -> None:
    result = KeywordIntentRecognizer().recognize("当前用户必吃榜包含哪些菜系")

    assert result.intent is IntentType.CUISINE_QUERY


def test_keyword_recognizer_returns_general_chat_for_unknown_message() -> None:
    result = KeywordIntentRecognizer().recognize("你好")

    assert result.intent is IntentType.GENERAL_CHAT


def test_keyword_recognizer_returns_combined_intents() -> None:
    result = KeywordIntentRecognizer().recognize(
        "帮我找一家日料，看看评分、营业时间和从学校过去要多久"
    )

    assert result.intent is IntentType.RESTAURANT_RECOMMENDATION
    assert set(result.intents) == {
        IntentType.RESTAURANT_RECOMMENDATION,
        IntentType.RATING_REVIEW_QUERY,
        IntentType.OPENING_HOURS_QUERY,
        IntentType.ROUTE_QUERY,
    }


def test_route_intent_requests_missing_origin_and_destination() -> None:
    result = KeywordIntentRecognizer().recognize("帮我查一下路线")

    assert result.missing_fields == ["origin", "destination"]
    assert result.clarifying_question


def test_conflicting_budget_constraints_are_reported() -> None:
    result = KeywordIntentRecognizer().recognize("找人均不超过100元但至少300元的餐厅")

    assert result.conflicts
