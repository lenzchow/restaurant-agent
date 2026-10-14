from __future__ import annotations

import asyncio

import pytest

from restaurant_agent.application.route_enrichment import RouteEnrichmentService
from restaurant_agent.contracts import Restaurant, RouteInfo


class FakeAmapClient:
    async def route_between(self, origin: str, destination: str, *, city=None):
        if destination == "Bad Address":
            raise ValueError("route unavailable")
        return RouteInfo(
            origin=origin,
            destination=destination,
            driving_distance_km=5,
            taxi_duration_minutes=12,
            transit_duration_minutes=25,
        )


@pytest.mark.asyncio
async def test_route_enrichment_preserves_restaurants_when_one_route_fails() -> None:
    restaurants = [
        Restaurant(
            name="Good Restaurant",
            cuisine="Japanese",
            address="Good Address",
            price_per_person=100,
            distance_km=1,
        ),
        Restaurant(
            name="Bad Restaurant",
            cuisine="Chinese",
            address="Bad Address",
            price_per_person=100,
            distance_km=2,
        ),
    ]

    enriched = await RouteEnrichmentService(FakeAmapClient()).enrich(
        restaurants, origin="学校", city="北京"
    )

    assert enriched[0].route is not None
    assert enriched[0].route.taxi_duration_minutes == 12
    assert enriched[1].route is None
    assert enriched[1].route_error == "route unavailable"


@pytest.mark.asyncio
async def test_route_enrichment_queries_restaurants_concurrently() -> None:
    started: list[str] = []
    release = asyncio.Event()

    class ConcurrentAmap:
        async def route_between(self, origin, destination, *, city=None):
            started.append(destination)
            if len(started) == 2:
                release.set()
            await release.wait()
            return RouteInfo(origin=origin, destination=destination)

    restaurants = [
        Restaurant(name="一", cuisine="菜", address="地址一", price_per_person=1, distance_km=1),
        Restaurant(name="二", cuisine="菜", address="地址二", price_per_person=1, distance_km=1),
    ]
    enriched = await asyncio.wait_for(
        RouteEnrichmentService(ConcurrentAmap()).enrich(
            restaurants, origin="起点", city="北京"
        ),
        timeout=1,
    )

    assert [item.route.destination for item in enriched] == ["地址一", "地址二"]
