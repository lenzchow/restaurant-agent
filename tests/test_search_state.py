from restaurant_agent.application.agent_planning import AgentParameterExtractor
from restaurant_agent.application.search_state import (
    SearchConditionManager,
    SearchConditionStatus,
)


def test_ambiguous_budget_returns_choices_instead_of_silent_value() -> None:
    manager = SearchConditionManager(AgentParameterExtractor())

    update = manager.update("我想找一家不要太贵的日料")

    assert update.status is SearchConditionStatus.NEEDS_CLARIFICATION
    assert update.candidates["max_budget"] == ["100", "200"]
    assert "100" in update.clarifying_question
    assert "200" in update.clarifying_question


def test_new_condition_overwrites_previous_condition() -> None:
    manager = SearchConditionManager(AgentParameterExtractor())

    manager.update("在北京海淀区找日料，人均100元以内，距离5公里以内")
    update = manager.update("改成人均200元以内")

    assert update.current_conditions.max_budget == 200
    assert update.current_conditions.max_distance_km == 5
    assert update.current_conditions.city == "北京"
    assert update.current_conditions.location == "海淀区"


def test_unlimited_condition_clears_previous_value() -> None:
    manager = SearchConditionManager(AgentParameterExtractor())

    manager.update("在北京找日料，人均100元以内")
    update = manager.update("预算不限")

    assert update.current_conditions.max_budget is None
    assert update.current_conditions.city == "北京"
    assert update.current_conditions.cuisine == "日料"


def test_confirm_returns_current_search_conditions() -> None:
    manager = SearchConditionManager(AgentParameterExtractor())

    manager.update("在北京海淀区找日料，人均100元以内")
    confirmed = manager.confirm()

    assert confirmed is not None
    assert confirmed.city == "北京"
    assert confirmed.location == "海淀区"
    assert confirmed.max_budget == 100
