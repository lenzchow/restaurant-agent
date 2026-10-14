# Platform-Agnostic Restaurant Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested, platform-neutral restaurant-finding HTTP agent using FastAPI, Pydantic, the OpenAI Agents SDK, and the Responses API-backed runtime.

**Architecture:** FastAPI exposes a generic `/v1/chat` contract. The application service invokes one Agents SDK agent whose only business tool is a typed restaurant search provider. The first provider is deterministic sample data; external platform adapters and live restaurant providers can be added without changing the HTTP contract or agent orchestration.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, `openai-agents`, pytest, httpx.

**Spec:** `docs/superpowers/specs/2026-10-14-platform-agnostic-restaurant-agent-design.md`

## Global Constraints

- Keep the core platform-neutral; no Feishu-specific code in the MVP.
- Use Pydantic models for all public request, response, tool-input, and restaurant records.
- Keep the restaurant provider replaceable through a protocol.
- Offline tests must not call OpenAI or an external restaurant service.
- Do not add a real provider without a selected API and credentials.

### Task 1: Project scaffolding and dependency contract

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/restaurant_agent/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces an installable Python package named `restaurant-agent` and pytest configuration for the later tasks.

- [ ] **Step 1: Write the dependency and test configuration**

Add runtime dependencies for `fastapi`, `uvicorn[standard]`, `pydantic-settings`, and `openai-agents`; add test dependencies for `pytest` and `httpx`. Configure pytest to discover `tests/` and `src/` imports.

- [ ] **Step 2: Verify the configuration is parseable**

Run: `python -m pip install -e '.[test]'`

Expected: the package and test dependencies install successfully, or the command reports the environment's dependency-installation limitation.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml .env.example src/restaurant_agent/__init__.py tests/conftest.py
git commit -m "chore: scaffold restaurant agent package"
```

### Task 2: Typed contracts and sample restaurant provider

**Files:**
- Create: `src/restaurant_agent/contracts.py`
- Create: `src/restaurant_agent/providers.py`
- Create: `tests/test_contracts.py`
- Create: `tests/test_providers.py`

**Interfaces:**
- Produces `ChatRequest`, `Restaurant`, `RestaurantSearchInput`, `ChatResponse`, and `RestaurantSearchProvider`.
- Produces `SampleRestaurantProvider.search(input: RestaurantSearchInput) -> list[Restaurant]`.

- [ ] **Step 1: Write failing contract and provider tests**

Test that `ChatRequest(message="find dinner")` gets a generated `conversation_id` only when the model defines a default factory, that `Restaurant` serializes stable field names, that cuisine and budget filters work, and that `limit=0` is rejected.

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_contracts.py tests/test_providers.py -q`

Expected: FAIL because the package modules do not yet exist.

- [ ] **Step 3: Implement the minimal models and provider**

Define strict-enough Pydantic models and a small in-memory catalog. The provider must apply only supplied filters and then slice to `limit`; it must not claim live availability.

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_contracts.py tests/test_providers.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/restaurant_agent/contracts.py src/restaurant_agent/providers.py tests/test_contracts.py tests/test_providers.py
git commit -m "feat: add typed restaurant contracts and sample provider"
```

### Task 3: Agents SDK service

**Files:**
- Create: `src/restaurant_agent/agent.py`
- Create: `tests/test_agent.py`

**Interfaces:**
- Produces `RestaurantAgentService(provider: RestaurantSearchProvider)`.
- Produces `async answer(request: ChatRequest) -> ChatResponse`.

- [ ] **Step 1: Write a failing service test with a fake runner boundary**

Test that the service returns a `ChatResponse` for a request and that the search tool can be called with typed `RestaurantSearchInput`. Keep the test offline by injecting a fake provider and mocking the SDK runner boundary.

- [ ] **Step 2: Run the focused test**

Run: `pytest tests/test_agent.py -q`

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement the agent service**

Define one `Agent` with concise restaurant-search instructions, register a function tool that delegates to the injected provider, and call it through `Runner.run`. Use the SDK's final output for the user-facing message and preserve the typed recommendation list in `ChatResponse`. Keep the model configurable through settings with a compatibility default of `gpt-4o-mini`; do not hard-code platform behavior.

- [ ] **Step 4: Run the focused test**

Run: `pytest tests/test_agent.py -q`

Expected: PASS without an API request.

- [ ] **Step 5: Commit**

```bash
git add src/restaurant_agent/agent.py tests/test_agent.py
git commit -m "feat: add restaurant agents sdk service"
```

### Task 4: FastAPI transport and health endpoint

**Files:**
- Create: `src/restaurant_agent/api.py`
- Create: `src/restaurant_agent/settings.py`
- Create: `tests/test_api.py`

**Interfaces:**
- Produces `app: FastAPI`.
- Produces `POST /v1/chat` accepting `ChatRequest` and returning `ChatResponse`.
- Produces `GET /health` returning `{"status": "ok"}`.

- [ ] **Step 1: Write failing API tests**

Use `httpx.AsyncClient` with an ASGI transport and an injected fake service. Test the health response, successful chat response, and FastAPI's 422 response for a missing message.

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/test_api.py -q`

Expected: FAIL because the application module does not exist.

- [ ] **Step 3: Implement the API factory and dependency injection**

Create settings from environment variables, construct the sample provider and agent service as the default dependency, and expose the two endpoints. Catch unexpected service errors at the boundary, log a safe message, and return a generic 500 response.

- [ ] **Step 4: Run the focused tests**

Run: `pytest tests/test_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/restaurant_agent/api.py src/restaurant_agent/settings.py tests/test_api.py
git commit -m "feat: expose platform-neutral chat api"
```

### Task 5: Documentation and full verification

**Files:**
- Create: `README.md`
- Modify: `.env.example`

**Interfaces:**
- Documents local setup, offline tests, API usage, and the future platform-adapter boundary.

- [ ] **Step 1: Write the local usage documentation**

Document `python -m pip install -e '.[test]'`, `uvicorn restaurant_agent.api:app --reload`, the `POST /v1/chat` JSON shape, and the fact that sample data is not live restaurant data.

- [ ] **Step 2: Run all offline verification**

Run: `pytest -q && python -m compileall src`

Expected: all tests pass and compilation exits with status 0.

- [ ] **Step 3: Run a no-key import smoke test**

Run: `python -c "from restaurant_agent.api import app; print(app.title)"`

Expected: prints the FastAPI application title without requiring `OPENAI_API_KEY`.

- [ ] **Step 4: Review the diff**

Run: `git diff --check && git status --short`

Expected: no whitespace errors; only files belonging to this implementation are changed.

- [ ] **Step 5: Commit**

```bash
git add README.md .env.example
git commit -m "docs: document restaurant agent mvp"
```
