# Dianping Browser Provider and Batch Routes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browser-harness-backed Dianping provider for live restaurant metadata and connect its restaurant results to the existing Amap route client.

**Architecture:** `DianpingBrowserProvider` owns all Dianping navigation and extraction, while application code consumes typed restaurant records. A separate batch-route service calls the existing `AmapMCPClient` for each restaurant and returns enriched records. Offline tests use a fake browser harness and fake Amap client; live smoke tests are opt-in and require the user’s existing browser session.

**Tech Stack:** Python 3.11+, Pydantic v2, browser-harness CLI, existing Amap MCP client, pytest.

**Spec:** Approved user requirements in the 2026-10-14 conversation; existing platform-neutral design in `docs/superpowers/specs/2026-10-14-platform-agnostic-restaurant-agent-design.md`.

## Global Constraints

- Navigate only Dianping domains: `dianping.com`, `www.dianping.com`, and `m.dianping.com`.
- Reuse the local browser’s existing session only; never log, export, or persist cookies/tokens.
- Real browser smoke tests are separate from offline tests and may stop for login, CAPTCHA, or permission prompts.
- Real restaurant data replaces the fake provider through an interface; it does not alter the platform-neutral API contract.
- Amap route failures must remain visible as missing route data, never fabricated values.

### Task 1: Add live restaurant metadata contracts and batch-route service

**Files:**
- Modify: `src/restaurant_agent/domain/contracts.py`
- Create: `src/restaurant_agent/application/route_enrichment.py`
- Test: `tests/test_route_enrichment.py`

**Interfaces:**
- `Restaurant` stores source URL and fetch timestamp in addition to existing metadata.
- `RouteEnrichmentService.enrich(restaurants, origin, city) -> list[Restaurant]` calls `AmapMCPClient.route_between` for each restaurant address and preserves restaurants when a route call fails.

- [ ] Write a fake Amap client test for multiple restaurants and one route failure.
- [ ] Run the focused test and confirm it fails because the service does not exist.
- [ ] Implement the typed route enrichment service.
- [ ] Run the focused test and confirm it passes.

### Task 2: Define the browser-harness adapter boundary

**Files:**
- Create: `src/restaurant_agent/infrastructure/browser_harness.py`
- Test: `tests/test_browser_harness.py`

**Interfaces:**
- `BrowserHarness` protocol exposes `run(script: str) -> str`.
- `SubprocessBrowserHarness` invokes the configured `browser-harness` executable without writing session data.
- Non-Dianping URLs are rejected before execution.

- [ ] Write tests for allowed Dianping URLs, rejected external URLs, and command output handling.
- [ ] Run focused tests red.
- [ ] Implement the adapter with argument-safe subprocess execution.
- [ ] Run focused tests green.

### Task 3: Implement Dianping extraction provider

**Files:**
- Create: `src/restaurant_agent/infrastructure/dianping_provider.py`
- Modify: `src/restaurant_agent/infrastructure/providers.py`
- Test: `tests/test_dianping_provider.py`

**Interfaces:**
- `DianpingBrowserProvider.get_restaurant_details(url_or_name, city) -> Restaurant`.
- `DianpingBrowserProvider.get_ranking(ranking_url_or_name, city, limit) -> list[Restaurant]`.
- Recommendation extraction returns up to 10 items and an explicit `recommendation_note` when fewer than 10 are available.

- [ ] Write fake-harness tests for detail extraction, fewer-than-10 recommendation notes, and ranking extraction.
- [ ] Run focused tests red.
- [ ] Implement JSON-first extraction from browser output and typed validation.
- [ ] Run focused tests green.

### Task 4: Wire live provider and document smoke tests

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Modify: `src/restaurant_agent/api.py`
- Modify: `README.md`
- Test: `tests/test_agent.py`

**Interfaces:**
- The application can accept an injected live provider and optional route enrichment service without changing `/v1/chat`.
- Live browser usage is not run during normal pytest.

- [ ] Write an offline service test that enriches live-provider-shaped restaurant records.
- [ ] Run it red, implement the injection path, then run it green.
- [ ] Run full offline tests, compile checks, and diff checks.
- [ ] Run a controlled `browser-harness --doctor` check and report whether the local session is available; do not claim live Dianping extraction unless a real page is successfully read.
