from __future__ import annotations

from types import SimpleNamespace

import pytest

from restaurant_agent.agent import RestaurantAgentService
from restaurant_agent.contracts import (
    ChatRequest,
    ChatResponse,
    RestaurantSearchInput,
    RouteInfo,
)
from restaurant_agent.intents.models import IntentType
from restaurant_agent.providers import SampleRestaurantProvider


@pytest.mark.asyncio
async def test_service_returns_typed_response_without_network() -> None:
    async def fake_runner(*args, **kwargs):
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="I found one option.",
                recommendations=[],
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
    )

    response = await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="Find dinner",
        )
    )

    assert response.message == "I found one option."
    assert response.conversation_id == "conversation-test"


@pytest.mark.asyncio
async def test_search_tool_uses_injected_provider() -> None:
    service = RestaurantAgentService(provider=SampleRestaurantProvider())

    results = await service.search_restaurants(
        RestaurantSearchInput(cuisine="Italian", limit=1)
    )

    assert len(results) == 1
    assert results[0].cuisine == "Italian"


@pytest.mark.asyncio
async def test_service_passes_recognized_intent_to_agent_runner() -> None:
    captured: dict[str, str] = {}

    async def fake_runner(*args, **kwargs):
        captured["input"] = args[1]
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="可以看看这家店的推荐菜。",
                intent=IntentType.DISH_RECOMMENDATION,
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
    )

    response = await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="这家店有什么推荐菜？",
        )
    )

    assert '"intent": "dish_recommendation"' in captured["input"]
    assert response.intent is IntentType.DISH_RECOMMENDATION


@pytest.mark.asyncio
async def test_service_passes_structured_agent_plan_to_runner() -> None:
    captured: dict[str, str] = {}

    async def fake_runner(*args, **kwargs):
        captured["input"] = args[1]
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test", message="已规划。"
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
    )

    await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="在杭州西湖区找3家日料，按评价最多排序",
        )
    )

    assert '"city": "杭州"' in captured["input"]
    assert '"limit": 3' in captured["input"]
    assert '"review_count"' in captured["input"]
    assert '"search_restaurants"' in captured["input"]
    assert '"compose_response"' in captured["input"]


@pytest.mark.asyncio
async def test_service_reuses_agents_sdk_session_for_follow_up_turns() -> None:
    sessions: list[object] = []

    async def fake_runner(*args, **kwargs):
        sessions.append(kwargs["session"])
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test", message="已规划。"
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
    )
    base = ChatRequest(
        conversation_id="conversation-test",
        user_id="user-test",
        message="在杭州找日料",
    )

    await service.answer(base)
    await service.answer(base.model_copy(update={"message": "人均200元以内"}))

    assert len(sessions) == 2
    assert sessions[0] is sessions[1]


def test_service_analyzes_missing_route_conditions_without_network() -> None:
    service = RestaurantAgentService(provider=SampleRestaurantProvider())

    analysis = service.analyze_request(
        ChatRequest(user_id="user-test", message="帮我查一下路线")
    )

    assert analysis.intent is IntentType.ROUTE_QUERY
    assert analysis.missing_fields == ["origin", "destination"]


@pytest.mark.asyncio
async def test_service_injects_mcp_route_into_agent_response() -> None:
    class FakeAmapClient:
        async def route_between(self, origin: str, destination: str, *, city=None):
            assert origin == "学校"
            assert destination == "Sakura Table"
            return RouteInfo(
                origin=origin,
                destination=destination,
                driving_distance_km=12,
                taxi_duration_minutes=30,
                transit_duration_minutes=40,
                matched_address="北京市朝阳区示例路88号",
            )

    async def fake_runner(*args, **kwargs):
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="路线已查到。",
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
        amap_client=FakeAmapClient(),
    )

    response = await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="查从学校到Sakura Table的路线",
        )
    )

    assert response.route is not None
    assert response.route.taxi_duration_minutes == 30


@pytest.mark.asyncio
async def test_service_exposes_dianping_detail_and_search_operations() -> None:
    class FakeDianpingProvider:
        async def get_restaurant_details(self, url_or_name: str, *, city=None):
            return SampleRestaurantProvider().search(RestaurantSearchInput(limit=1))[0]

        async def search_restaurants(self, request):
            return SampleRestaurantProvider().search(RestaurantSearchInput(limit=request.limit))

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        dianping_provider=FakeDianpingProvider(),
    )

    detail = await service.get_restaurant_details("Sakura Table", city="北京")
    results = await service.search_restaurants(
        RestaurantSearchInput(city="北京", cuisine="北京菜", page=2, limit=2)
    )

    assert detail.name == "Pasta House"
    assert len(results) == 2


@pytest.mark.asyncio
async def test_service_exposes_dishes_and_review_summary_tools() -> None:
    class FakeDianpingProvider:
        async def get_restaurant_details(self, url_or_name: str, *, city=None):
            return SampleRestaurantProvider().search(RestaurantSearchInput(limit=1))[0]

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        dianping_provider=FakeDianpingProvider(),
    )

    dishes = await service.get_recommended_dishes("Pasta House", city="北京")
    summary = await service.get_review_summary("Pasta House", city="北京")

    assert dishes == {
        "dishes": ["松露奶油意面", "提拉米苏"],
        "images": [],
        "image_note": "页面未抓取到推荐菜图片。",
    }
    assert summary["restaurant"] == "Pasta House"
    assert summary["summary"] == "环境安静，意面口味稳定"


@pytest.mark.asyncio
async def test_query_route_marks_unsupported_requested_modes() -> None:
    class FakeAmapClient:
        async def route_between(self, origin: str, destination: str, *, city=None):
            return RouteInfo(origin=origin, destination=destination)

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        amap_client=FakeAmapClient(),
    )

    route = await service.query_route(
        "学校",
        "餐厅",
        modes=["driving", "bicycle", "motorcycle"],
    )

    assert route.requested_modes == ["driving", "bicycle", "motorcycle"]
    assert route.unsupported_modes == ["bicycle", "motorcycle"]


@pytest.mark.asyncio
async def test_service_enriches_dianping_results_with_batch_routes() -> None:
    class FakeDianpingProvider:
        async def search_restaurants(self, request):
            return SampleRestaurantProvider().search(RestaurantSearchInput(limit=request.limit))

    class FakeRouteEnrichment:
        async def enrich(self, restaurants, *, origin, city=None):
            return [item.model_copy(update={"route_error": f"from:{origin}"}) for item in restaurants]

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        dianping_provider=FakeDianpingProvider(),
        route_enrichment=FakeRouteEnrichment(),
    )

    restaurants = await service.search_restaurants(
        RestaurantSearchInput(city="北京", limit=2), origin="学校"
    )

    assert len(restaurants) == 2
    assert restaurants[0].route_error == "from:学校"


@pytest.mark.asyncio
async def test_live_restaurant_request_requires_confirmation_before_runner() -> None:
    calls = 0

    class FakeDianpingProvider:
        async def get_restaurant_details(self, url_or_name: str, *, city=None):
            raise AssertionError("browser provider must not run before approval")

    async def fake_runner(*args, **kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="已完成。",
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
        dianping_provider=FakeDianpingProvider(),
    )

    response = await service.answer(
        ChatRequest(
            conversation_id="conversation-test",
            user_id="user-test",
            message="帮我找一家日料",
        )
    )

    assert response.status == "confirmation_required"
    assert response.requires_confirmation is True
    assert response.operation_id is None
    assert response.search_conditions is not None
    assert response.search_conditions.cuisine == "日料"
    assert calls == 0


@pytest.mark.asyncio
async def test_approval_resumes_original_request() -> None:
    calls = 0

    class FakeDianpingProvider:
        async def get_restaurant_details(self, url_or_name: str, *, city=None):
            return SampleRestaurantProvider().search(RestaurantSearchInput(limit=1))[0]

    async def fake_runner(*args, **kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            final_output=ChatResponse(
                conversation_id="conversation-test",
                message="已完成。",
            )
        )

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        runner=fake_runner,
        dianping_provider=FakeDianpingProvider(),
    )
    original = ChatRequest(
        conversation_id="conversation-test",
        user_id="user-test",
        message="帮我找一家日料",
    )
    pending = await service.answer(original)

    conditions_approved = await service.answer(
        ChatRequest(
            conversation_id=original.conversation_id,
            user_id=original.user_id,
            message="确认",
            confirmation="approve",
        )
    )
    browser_approved = await service.answer(
        ChatRequest(
            conversation_id=original.conversation_id,
            user_id=original.user_id,
            message="确认",
            confirmation="approve",
        )
    )

    assert pending.status == "confirmation_required"
    assert conditions_approved.status == "confirmation_required"
    assert conditions_approved.operation_id
    assert browser_approved.status == "completed"
    assert calls == 1


@pytest.mark.asyncio
async def test_ambiguous_search_condition_returns_choices_before_search() -> None:
    class FakeDianpingProvider:
        async def search_restaurants(self, request):
            raise AssertionError("search must wait for condition choice")

    service = RestaurantAgentService(
        provider=SampleRestaurantProvider(),
        dianping_provider=FakeDianpingProvider(),
    )

    response = await service.answer(
        ChatRequest(user_id="user-test", message="找一家不要太贵的日料")
    )

    assert response.condition_candidates == {"max_budget": [100, 200]}
    assert "100" in response.message
    assert "200" in response.message
