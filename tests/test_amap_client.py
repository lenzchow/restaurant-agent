from __future__ import annotations

from types import SimpleNamespace

import pytest

from restaurant_agent.infrastructure.amap_client import AmapMCPClient


class FakeMCPServer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def call_tool(self, name: str, arguments: dict[str, object]):
        self.calls.append((name, arguments))
        payloads = {
            "maps_text_search": {
                "pois": [
                    {
                        "id": "B001",
                        "name": "Sakura Table",
                        "address": "北京市朝阳区示例路88号",
                        "location": "116.4302,39.9921",
                        "cityname": "北京",
                    }
                ]
            },
            "maps_direction_driving": {
                "route": {"paths": [{"distance": "12000", "duration": "1800"}]}
            },
            "maps_schema_take_taxi": {
                "uri": "amapuri://route/take taxi",
            },
            "maps_direction_transit_integrated": {
                "route": {
                    "transits": [
                        {
                            "duration": "2400",
                            "segments": [
                                {"bus": {"buslines": [{"name": "地铁10号线"}]}},
                                {"railway": {"name": "地铁5号线"}},
                            ],
                        }
                    ]
                }
            },
        }
        payload = payloads[name]
        return SimpleNamespace(content=[SimpleNamespace(text=str(payload).replace("'", '"'))])


@pytest.mark.asyncio
async def test_client_searches_place_and_normalizes_route() -> None:
    server = FakeMCPServer()
    client = AmapMCPClient(server)

    route = await client.route_between("北京信息科技大学小营校区", "Sakura Table", city="北京")

    assert route.matched_address == "北京市朝阳区示例路88号"
    assert route.driving_distance_km == 12
    assert route.taxi_duration_minutes == 30
    assert route.transit_duration_minutes == 40
    assert route.subway_lines == ["地铁10号线", "地铁5号线"]
    assert route.taxi_uri == "amapuri://route/take taxi"
    assert [name for name, _ in server.calls] == [
        "maps_text_search",
        "maps_text_search",
        "maps_direction_driving",
        "maps_schema_take_taxi",
        "maps_direction_transit_integrated",
    ]


@pytest.mark.asyncio
async def test_client_uses_poi_detail_when_text_search_has_no_location() -> None:
    class DetailServer:
        async def call_tool(self, name: str, arguments: dict[str, object]):
            if name == "maps_text_search":
                payload = {"pois": [{"id": "B001", "name": "Sakura Table", "address": "示例路88号"}]}
            else:
                payload = {"id": "B001", "name": "Sakura Table", "location": "116.4,39.9", "address": "示例路88号"}
            return SimpleNamespace(content=[SimpleNamespace(text=str(payload).replace("'", '"'))])

    place = await AmapMCPClient(DetailServer()).search_place("Sakura Table", city="北京")

    assert place.location == "116.4,39.9"


def test_client_extracts_taxi_uri_from_plain_text() -> None:
    uri = AmapMCPClient._find_string(
        {"raw_text": "请直接打开 amapuri://drive/takeTaxi?dname=test"},
        "uri",
    )

    assert uri == "amapuri://drive/takeTaxi?dname=test"


@pytest.mark.asyncio
async def test_route_between_retries_transient_tool_failure() -> None:
    calls = 0
    base = FakeMCPServer()

    class RetryServer:
        async def call_tool(self, name: str, arguments: dict[str, object]):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise TimeoutError("temporary timeout")
            return await base.call_tool(name, arguments)

    route = await AmapMCPClient(RetryServer()).route_between("起点", "终点")

    assert route.destination == "Sakura Table"
    assert calls > 1
