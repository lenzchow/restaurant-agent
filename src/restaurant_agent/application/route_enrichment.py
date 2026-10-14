from __future__ import annotations

import asyncio
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
        async def enrich_one(restaurant: Restaurant) -> Restaurant:
            try:
                route = await self.amap_client.route_between(
                    origin,
                    restaurant.address,
                    city=city,
                )
                return restaurant.model_copy(update={"route": route})
            except Exception as exc:
                return restaurant.model_copy(update={"route_error": str(exc)})

        return list(await asyncio.gather(*(enrich_one(item) for item in restaurants)))
