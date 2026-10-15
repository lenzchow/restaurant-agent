from restaurant_agent.application.agent_planning import (
    AgentAction,
    AgentParameterExtractor,
    ToolRouter,
    WorkflowStepType,
)
from restaurant_agent.domain.contracts import RestaurantSearchInput
from restaurant_agent.intents.models import IntentResult, IntentType


def test_parameter_extractor_builds_search_request_from_natural_language() -> None:
    result = AgentParameterExtractor().extract(
        "帮我在杭州西湖区找3家日料，人均200元以内，按评价最多排序"
    )

    assert result.search_request == RestaurantSearchInput(
        city="杭州",
        location="西湖区",
        cuisine="日料",
        max_budget=200,
        limit=3,
        sort="review_count",
    )


def test_parameter_extractor_extracts_route_endpoints() -> None:
    result = AgentParameterExtractor().extract("查从杭州东站到西湖区某餐厅的路线")

    assert result.route_origin == "杭州东站"
    assert result.route_destination == "西湖区某餐厅"


def test_parameter_extractor_extracts_requested_route_modes() -> None:
    result = AgentParameterExtractor().extract(
        "查从学校到餐厅的开车、打车、公交、地铁、骑单车和骑摩托车路线"
    )

    assert result.route_modes == [
        "driving",
        "taxi",
        "bus",
        "subway",
        "bicycle",
        "motorcycle",
    ]


def test_parameter_extractor_extracts_dianping_restaurant_url() -> None:
    result = AgentParameterExtractor().extract(
        "查询 https://www.dianping.com/shop/example 的推荐菜"
    )

    assert result.restaurant_url == "https://www.dianping.com/shop/example"


def test_parameter_extractor_reports_confidence_and_unknown_fields() -> None:
    result = AgentParameterExtractor().extract("找一家环境好一些的馆子")

    assert result.confidence < 1
    assert "sort" in result.unrecognized_fields


def test_parameter_extractor_extracts_party_distance_and_page() -> None:
    result = AgentParameterExtractor().extract(
        "在北京找2家火锅，4个人，距离3公里以内，第2页"
    )

    assert result.search_request.party_size == 4
    assert result.search_request.max_distance_km == 3
    assert result.search_request.page == 2


def test_parameter_extractor_extracts_restaurant_name_for_detail_queries() -> None:
    result = AgentParameterExtractor().extract("查询全聚德前门店的详细信息")

    assert result.restaurant_name == "全聚德前门店"


def test_tool_router_plans_multiple_actions() -> None:
    intent = IntentResult(
        intent=IntentType.RESTAURANT_RECOMMENDATION,
        intents=[
            IntentType.RESTAURANT_RECOMMENDATION,
            IntentType.DISH_RECOMMENDATION,
            IntentType.ROUTE_QUERY,
        ],
        confidence=0.9,
        route_origin="杭州东站",
        route_destination="某餐厅",
    )

    plan = ToolRouter().plan(intent)

    assert plan == [
        AgentAction.SEARCH_RESTAURANTS,
        AgentAction.GET_RESTAURANT_DETAILS,
        AgentAction.QUERY_ROUTE,
    ]


def test_tool_router_plans_details_and_review_summary_actions() -> None:
    router = ToolRouter()

    details = router.plan(
        IntentResult(
            intent=IntentType.RESTAURANT_DETAILS_QUERY,
            intents=[IntentType.RESTAURANT_DETAILS_QUERY],
            confidence=0.9,
        )
    )
    review_summary = router.plan(
        IntentResult(
            intent=IntentType.REVIEW_SUMMARY_QUERY,
            intents=[IntentType.REVIEW_SUMMARY_QUERY],
            confidence=0.9,
        )
    )

    assert details == [AgentAction.GET_RESTAURANT_DETAILS]
    assert review_summary == [AgentAction.GET_RESTAURANT_DETAILS]


def test_tool_router_builds_ordered_workflow_steps_for_composite_request() -> None:
    intent = IntentResult(
        intent=IntentType.RESTAURANT_RECOMMENDATION,
        intents=[
            IntentType.RESTAURANT_RECOMMENDATION,
            IntentType.DISH_RECOMMENDATION,
            IntentType.REVIEW_SUMMARY_QUERY,
            IntentType.ROUTE_QUERY,
        ],
        confidence=0.9,
    )

    workflow = ToolRouter().workflow(intent)

    assert [step.type for step in workflow.steps] == [
        WorkflowStepType.SEARCH_RESTAURANTS,
        WorkflowStepType.GET_RESTAURANT_DETAILS,
        WorkflowStepType.GET_RECOMMENDED_DISHES,
        WorkflowStepType.GET_REVIEWS,
        WorkflowStepType.SUMMARIZE_REVIEWS,
        WorkflowStepType.QUERY_ROUTE,
        WorkflowStepType.COMPOSE_RESPONSE,
    ]
    assert workflow.steps[-1].depends_on == [step.id for step in workflow.steps[:-1]]


def test_tool_router_keeps_requested_route_modes_in_workflow() -> None:
    intent = IntentResult(
        intent=IntentType.ROUTE_QUERY,
        intents=[IntentType.ROUTE_QUERY],
        confidence=0.9,
    )

    workflow = ToolRouter().workflow(
        intent, route_modes=["driving", "bicycle", "motorcycle"]
    )

    assert workflow.route_modes == ["driving", "bicycle", "motorcycle"]
