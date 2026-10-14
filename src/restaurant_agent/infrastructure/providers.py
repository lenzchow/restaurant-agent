from __future__ import annotations

from typing import Protocol

from restaurant_agent.domain.contracts import Restaurant, RestaurantSearchInput


class RestaurantSearchProvider(Protocol):
    def search(self, request: RestaurantSearchInput) -> list[Restaurant]:
        ...


class SampleRestaurantProvider:
    """Deterministic local provider used until a live data source is selected."""

    _restaurants = [
        Restaurant(
            name="Pasta House",
            cuisine="Italian",
            address="1 Main Street",
            price_per_person=120,
            distance_km=1.2,
            recommended_dishes=["松露奶油意面", "提拉米苏"],
            opening_hours="11:00-22:00",
            rating=4.5,
            review_summary="环境安静，意面口味稳定",
        ),
        Restaurant(
            name="Sakura Table",
            cuisine="Japanese",
            address="88 River Road",
            price_per_person=180,
            distance_km=2.4,
            recommended_dishes=["寿司拼盘", "烤鳗鱼"],
            opening_hours="11:30-21:30",
            rating=4.7,
            review_summary="食材新鲜，适合约会",
        ),
        Restaurant(
            name="Chongqing Kitchen",
            cuisine="Sichuan",
            address="16 South Avenue",
            price_per_person=90,
            distance_km=3.1,
            recommended_dishes=["水煮鱼", "辣子鸡"],
            opening_hours="10:30-22:30",
            rating=4.3,
            review_summary="口味偏辣，性价比高",
        ),
    ]

    def search(self, request: RestaurantSearchInput) -> list[Restaurant]:
        results = self._restaurants
        if request.cuisine:
            cuisine = request.cuisine.casefold()
            results = [item for item in results if cuisine in item.cuisine.casefold()]
        if request.location:
            location = request.location.casefold()
            results = [item for item in results if location in item.address.casefold()]
        if request.max_budget is not None:
            results = [item for item in results if item.price_per_person <= request.max_budget]
        if request.max_distance_km is not None:
            results = [item for item in results if item.distance_km <= request.max_distance_km]
        return results[: request.limit]
