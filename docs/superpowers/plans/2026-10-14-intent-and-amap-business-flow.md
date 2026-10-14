# Intent and Amap Business Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add combined restaurant intents, clarification/conflict handling, fake restaurant metadata, and real Amap MCP business-call normalization without coupling the core to a live restaurant provider.

**Architecture:** Keep intent recognition and request analysis in the application boundary, keep fake/live restaurant records behind the Provider protocol, and isolate MCP tool names plus response normalization in `infrastructure/amap_client.py`. The Agent service will expose structured analysis and route results while preserving the platform-neutral HTTP contract.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, OpenAI Agents SDK MCP, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-10-14-platform-agnostic-restaurant-agent-design.md` plus the approved conversation design on 2026-10-14.

## Global Constraints

- Real restaurant data is out of scope; use deterministic fake data until a real Provider is selected.
- Offline tests must not call external services; MCP business-call verification is a separate configured smoke test.
- Keep Amap-specific tool names and response parsing inside infrastructure code.
- Do not log or persist API keys, bearer tokens, or the resolved MCP URL.
- Preserve compatibility exports from the existing package-root modules.

### Task 1: Extend intent and response contracts

**Files:**
- Modify: `src/restaurant_agent/intents/models.py`
- Modify: `src/restaurant_agent/intents/classifier.py`
- Modify: `src/restaurant_agent/domain/contracts.py`
- Test: `tests/test_intents.py`
- Test: `tests/test_contracts.py`

**Interfaces:**
- `IntentType` adds route, opening-hours, and rating/review values.
- `IntentResult` contains `intents`, `missing_fields`, `clarifying_question`, and `conflicts`.
- `ChatResponse` exposes the same analysis fields plus `route_options` where needed.

- [ ] Write tests for single new intents, combined intents, missing route origin/destination, and explicit contradictory budget constraints.
- [ ] Run focused tests and confirm they fail because the fields and classifications do not exist.
- [ ] Implement the enum, result model, deterministic analysis, and response fields.
- [ ] Run focused tests and confirm they pass.

### Task 2: Add fake restaurant metadata and application analysis

**Files:**
- Modify: `src/restaurant_agent/infrastructure/providers.py`
- Modify: `src/restaurant_agent/application/service.py`
- Test: `tests/test_providers.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- `Restaurant` includes optional dishes, opening hours, rating, review summary, and ranking labels.
- `SampleRestaurantProvider` returns deterministic metadata.
- `RestaurantAgentService.analyze_request(request)` returns `IntentResult` without network access.

- [ ] Write tests that fake restaurants expose dishes/hours/ratings and service returns clarification data.
- [ ] Run focused tests and confirm they fail.
- [ ] Add fake metadata and connect analysis to the service input payload.
- [ ] Run focused tests and confirm they pass.

### Task 3: Implement Amap MCP business client

**Files:**
- Create: `src/restaurant_agent/infrastructure/amap_client.py`
- Modify: `src/restaurant_agent/domain/contracts.py`
- Modify: `src/restaurant_agent/infrastructure/amap_mcp.py`
- Test: `tests/test_amap_client.py`

**Interfaces:**
- `AmapMCPClient.search_place(query) -> PlaceResult`.
- `AmapMCPClient.get_route(origin, destination) -> RouteInfo`.
- The client calls `maps_text_search`, `maps_direction_driving`, `maps_schema_take_taxi`, and `maps_direction_transit_integrated`.
- The normalizer accepts MCP text/JSON content and never invents missing route values.

- [ ] Write fake-server tests for tool calls and normalization of driving, taxi, transit, subway line, and matched-address fields.
- [ ] Run focused tests and confirm they fail.
- [ ] Implement the client, tool invocation, and normalization.
- [ ] Run focused tests and confirm they pass.

### Task 4: Wire route intent and run live smoke verification

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Modify: `src/restaurant_agent/api.py`
- Modify: `README.md`
- Test: `tests/test_agent.py`

**Interfaces:**
- Route requests can use a configured `AmapMCPClient`; missing conditions return a clarification response before MCP calls.
- Restaurant recommendations can include normalized route data.

- [ ] Write an offline service test with a fake Amap client.
- [ ] Run it red, then wire the service and run it green.
- [ ] Run the full offline suite and compile check.
- [ ] With `.env` configured, call one fake restaurant address through the real MCP tools and report the returned fields without secrets.
