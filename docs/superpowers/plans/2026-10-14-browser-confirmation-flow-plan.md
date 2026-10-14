# Browser Confirmation Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require explicit user approval before a restaurant request can use the local Chrome/browser-harness session.

**Architecture:** Add a platform-neutral confirmation contract and an in-memory pending-operation manager. `RestaurantAgentService` creates a pending operation for Dianping-backed intents, returns a confirmation response, and resumes the original request only after an approve decision. Platform adapters can later render the same response as buttons or prompts.

**Tech Stack:** Python 3.11+, Pydantic v2, FastAPI, pytest.

**Spec:** Approved conversation design for browser confirmation on 2026-10-14.

## Global Constraints

- Never start browser-harness for a request that has not been approved.
- Keep confirmation state platform-neutral and independent of Feishu.
- Use in-memory state for this phase; no database or Redis is introduced.
- Route-only Amap requests do not require browser confirmation.

### Task 1: Add confirmation contracts and state manager

**Files:**
- Modify: `src/restaurant_agent/domain/contracts.py`
- Create: `src/restaurant_agent/application/confirmation.py`
- Test: `tests/test_confirmation.py`

**Interfaces:**
- `ChatRequest.confirmation` accepts `approve` or `reject`.
- `ChatResponse` exposes `status`, `operation_id`, `requires_confirmation`, and `requested_actions`.
- `ConfirmationManager.create/find/approve/reject` manages pending operations by conversation and user.

### Task 2: Gate Dianping-backed requests in Agent Service

**Files:**
- Modify: `src/restaurant_agent/application/service.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- A Dianping-backed intent returns `confirmation_required` before runner/provider execution.
- Approval resumes the original request once; rejection returns `rejected` without browser work.
- Amap-only route requests continue without browser confirmation.

### Task 3: Verify API contract and documentation

**Files:**
- Modify: `README.md`
- Test: `tests/test_api.py`

**Interfaces:**
- FastAPI serializes confirmation fields without platform-specific UI assumptions.
- Offline tests cover confirmation responses; real browser execution remains an opt-in smoke test.
