from __future__ import annotations

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
