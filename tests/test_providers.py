from __future__ import annotations

import pytest
from pydantic import ValidationError

from restaurant_agent.contracts import RestaurantSearchInput
from restaurant_agent.providers import SampleRestaurantProvider


def test_provider_filters_by_cuisine_and_budget() -> None:
    provider = SampleRestaurantProvider()

    results = provider.search(
        RestaurantSearchInput(cuisine="Italian", max_budget=150, limit=10)
    )

    assert results
    assert all(item.cuisine == "Italian" for item in results)
    assert all(item.price_per_person <= 150 for item in results)


def test_provider_respects_result_limit() -> None:
    provider = SampleRestaurantProvider()

    results = provider.search(RestaurantSearchInput(limit=1))

    assert len(results) == 1


def test_sample_provider_returns_restaurant_metadata() -> None:
    restaurant = SampleRestaurantProvider().search(RestaurantSearchInput(limit=1))[0]

    assert restaurant.recommended_dishes
    assert restaurant.opening_hours
    assert restaurant.rating is not None
    assert restaurant.review_summary


def test_search_limit_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        RestaurantSearchInput(limit=0)
