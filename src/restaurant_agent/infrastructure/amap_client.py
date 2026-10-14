from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from restaurant_agent.domain.contracts import RouteInfo


class PlaceResult(BaseModel):
    name: str
    address: str
    location: str
    poi_id: str | None = None
    city: str | None = None


class AmapMCPClient:
    """Business wrapper around the Amap MCP tool names and response shapes."""

    def __init__(self, server: Any) -> None:
        self.server = server

    async def search_place(self, query: str, city: str | None = None) -> PlaceResult:
        arguments: dict[str, object] = {"keywords": query}
        if city:
            arguments.update({"city": city, "citylimit": True})
        result = await self.server.call_tool("maps_text_search", arguments)
        payload = self._payload(result)
        pois = payload.get("pois", [])
        if not pois:
            raise ValueError(f"Amap did not find a place for query: {query}")
        place = pois[0]
        poi_id = place.get("id") or place.get("idname")
        detail: dict[str, Any] = {}
        if not place.get("location") and poi_id:
            detail = self._payload(
                await self.server.call_tool("maps_search_detail", {"id": poi_id})
            )
        return PlaceResult(
            name=str(detail.get("name") or place.get("name") or query),
            address=str(
                detail.get("address")
                or place.get("address")
                or place.get("pname")
                or query
            ),
            location=str(detail.get("location") or place.get("location") or ""),
            poi_id=poi_id,
            city=detail.get("city") or place.get("cityname") or city,
        )

    async def route_between(
        self,
        origin_query: str,
        destination_query: str,
        *,
        city: str | None = None,
    ) -> RouteInfo:
        origin = await self.search_place(origin_query, city)
        destination = await self.search_place(destination_query, city)
        if not origin.location or not destination.location:
            raise ValueError("Amap place search did not return coordinates")

        driving = self._payload(
            await self.server.call_tool(
                "maps_direction_driving",
                {"origin": origin.location, "destination": destination.location},
            )
        )
        taxi = self._payload(
            await self.server.call_tool(
                "maps_schema_take_taxi",
                self._taxi_arguments(origin, destination),
            )
        )
        transit = self._payload(
            await self.server.call_tool(
                "maps_direction_transit_integrated",
                {
                    "origin": origin.location,
                    "destination": destination.location,
                    "city": origin.city or city or "",
                    "cityd": destination.city or city or "",
                },
            )
        )
        driving_distance, driving_minutes = self._driving_values(driving)
        transit_minutes, subway_lines, bus_lines = self._transit_values(transit)
        return RouteInfo(
            origin=origin.name,
            destination=destination.name,
            driving_distance_km=driving_distance,
            # The Amap taxi MCP tool returns a launch URI, not an ETA. The
            # driving duration is the available minute estimate for now.
            taxi_duration_minutes=driving_minutes,
            transit_duration_minutes=transit_minutes,
            matched_address=destination.address,
            taxi_uri=self._find_string(taxi, "uri", "url", "taxi_uri"),
            subway_lines=subway_lines,
            bus_lines=bus_lines,
            queried_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _taxi_arguments(origin: PlaceResult, destination: PlaceResult) -> dict[str, str]:
        slon, slat = origin.location.split(",", maxsplit=1)
        dlon, dlat = destination.location.split(",", maxsplit=1)
        return {
            "slon": slon,
            "slat": slat,
            "sname": origin.name,
            "dlon": dlon,
            "dlat": dlat,
            "dname": destination.name,
        }

    @classmethod
    def _payload(cls, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        structured = getattr(result, "structuredContent", None)
        if isinstance(structured, dict):
            return structured
        texts: list[str] = []
        for block in getattr(result, "content", []) or []:
            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
            if text:
                texts.append(str(text))
        raw = "\n".join(texts).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_text": raw}
        return payload if isinstance(payload, dict) else {"value": payload}

    @staticmethod
    def _driving_values(payload: dict[str, Any]) -> tuple[float | None, int | None]:
        path = AmapMCPClient._first_mapping(payload, "paths") or payload
        distance = AmapMCPClient._number(path.get("distance"))
        duration = AmapMCPClient._number(path.get("duration"))
        return (
            round(distance / 1000, 2) if distance is not None else None,
            round(duration / 60) if duration is not None else None,
        )

    @staticmethod
    def _transit_values(payload: dict[str, Any]) -> tuple[int | None, list[str], list[str]]:
        transit = AmapMCPClient._first_mapping(payload, "transits") or {}
        duration = AmapMCPClient._number(transit.get("duration"))
        subway: list[str] = []
        buses: list[str] = []
        AmapMCPClient._collect_lines(transit, subway, buses)
        return (round(duration / 60) if duration is not None else None, subway, buses)

    @staticmethod
    def _collect_lines(value: Any, subway: list[str], buses: list[str]) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"name", "line_name"} and isinstance(item, str):
                    if "地铁" in item and item not in subway:
                        subway.append(item)
                    elif ("公交" in item or "路" in item) and item not in buses:
                        buses.append(item)
                AmapMCPClient._collect_lines(item, subway, buses)
        elif isinstance(value, list):
            for item in value:
                AmapMCPClient._collect_lines(item, subway, buses)

    @staticmethod
    def _first_mapping(value: Any, key: str) -> dict[str, Any] | None:
        if isinstance(value, dict):
            candidate = value.get(key)
            if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                return candidate[0]
            for item in value.values():
                found = AmapMCPClient._first_mapping(item, key)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = AmapMCPClient._first_mapping(item, key)
                if found:
                    return found
        return None

    @staticmethod
    def _find_string(payload: dict[str, Any], *keys: str) -> str | None:
        raw_text = payload.get("raw_text", "")
        match = re.search(r"(amapuri://\S+)", raw_text)
        if match:
            return match.group(1).rstrip("。.,，")
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                return value
        return None

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
