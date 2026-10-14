from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from restaurant_agent.domain.contracts import Restaurant


class RouteEnrichmentService:
    def __init__(self, amap_client: Any) -> None:
        self.amap_client = amap_client

    async def enrich(
        self,
        restaurants: Sequence[Restaurant],
        *,
        origin: str,
        city: str | None = None,
    ) -> list[Restaurant]:
        enriched: list[Restaurant] = []
        for restaurant in restaurants:
            try:
                route = await self.amap_client.route_between(
                    origin,
                    restaurant.address,
                    city=city,
                )
                enriched.append(restaurant.model_copy(update={"route": route}))
            except Exception as exc:
                enriched.append(
                    restaurant.model_copy(update={"route_error": str(exc)})
                )
        return enriched
