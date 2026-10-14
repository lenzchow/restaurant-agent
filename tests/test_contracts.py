from __future__ import annotations

import pytest
from pydantic import ValidationError

from restaurant_agent.contracts import (
    ChatRequest,
    ChatResponse,
    Restaurant,
    RestaurantSearchInput,
)
from restaurant_agent.intents.models import IntentType


def test_chat_request_accepts_message_and_generates_conversation_id() -> None:
    request = ChatRequest(user_id="user-1", message="Find dinner")

    assert request.message == "Find dinner"
    assert request.conversation_id


def test_restaurant_serializes_stable_fields() -> None:
    restaurant = Restaurant(
        name="Pasta House",
        cuisine="Italian",
        address="1 Main Street",
        price_per_person=120,
        distance_km=1.2,
    )

    assert restaurant.model_dump() == {
        "name": "Pasta House",
        "cuisine": "Italian",
        "address": "1 Main Street",
        "price_per_person": 120.0,
        "distance_km": 1.2,
        "recommended_dishes": [],
        "recommendation_note": None,
        "opening_hours": None,
        "rating": None,
        "review_summary": None,
        "review_highlights": [],
        "source_url": None,
        "source_fetched_at": None,
        "route": None,
        "route_error": None,
    }


def test_chat_response_contains_recommendations() -> None:
    response = ChatResponse(
        conversation_id="conversation-1",
        message="Here are two options.",
        recommendations=[],
    )

    assert response.recommendations == []


def test_restaurant_supports_fake_metadata() -> None:
    restaurant = Restaurant(
        name="Sakura Table",
        cuisine="Japanese",
        address="88 River Road",
        price_per_person=180,
        distance_km=2.4,
        recommended_dishes=["寿司拼盘"],
        opening_hours="11:00-22:00",
        rating=4.6,
        review_summary="食材新鲜",
    )

    assert restaurant.rating == 4.6
    assert restaurant.recommended_dishes == ["寿司拼盘"]


def test_restaurant_search_input_supports_dianping_filters_and_pagination() -> None:
    request = RestaurantSearchInput(
        city="北京",
        cuisine="北京菜",
        location="朝阳区",
        sort="rating",
        page=2,
        limit=10,
    )

    assert request.city == "北京"
    assert request.sort == "rating"
    assert request.page == 2


def test_chat_response_exposes_analysis_fields() -> None:
    response = ChatResponse(
        conversation_id="conversation-1",
        message="请补充起点和终点",
        intent=IntentType.ROUTE_QUERY,
        intents=[IntentType.ROUTE_QUERY],
        missing_fields=["origin", "destination"],
        clarifying_question="请提供起点和终点。",
    )

    assert response.missing_fields == ["origin", "destination"]


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(user_id="user-1", message=" ")
