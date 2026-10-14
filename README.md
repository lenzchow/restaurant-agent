# Restaurant Agent

A platform-neutral restaurant-finding agent built with FastAPI, Pydantic, the OpenAI Agents SDK, and the Responses API-backed runtime.

## Current MVP

The project exposes a generic HTTP API. It does not contain Feishu-specific code, so a Feishu bot, web UI, Slack app, or another platform can be added later as an adapter around the same request and response contracts.

The sample provider remains available for offline tests. The default configuration now uses the real Dianping browser provider when Chrome and browser-harness are available.

The intent layer supports restaurant search/filtering, dish recommendations, cuisine queries, route queries, opening-hours queries, and rating/review queries. It can return multiple intents together, ask for missing route endpoints, and report contradictory budget constraints.

The `DianpingBrowserProvider` uses the local `browser-harness` session for Dianping-only restaurant search and detail pages. It resolves the selected city, cuisine, neighborhood, and sort links from the live Dianping page, so it is not limited to Beijing or a fixed code table. Supported sort intents include smart, good reviews, popularity, taste, most reviews, best environment, best service, booking priority, and per-person price high/low. The `page` and `limit` fields control pagination and returned card count. It does not implement real Dianping ranking-list scraping, and it does not persist browser cookies or tokens. Detail extraction limits recommended dishes to 10 and records a note when fewer are visible.

When a Dianping-backed request arrives, the service first returns `status=confirmation_required` with an `operation_id` and requested browser actions. The platform adapter should show that confirmation to the user. Approve with `confirmation: "approve"` using the same `conversation_id` and `user_id`; reject with `confirmation: "reject"`. The in-memory confirmation state is intended for the MVP and should move to shared storage before multi-instance deployment.

## Setup

Requires Python 3.11+ and `uv`.

```bash
uv sync --extra test
cp .env.example .env
```

Set `OPENAI_API_KEY` in `.env` before calling the agent. `OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`.

To enable the remote Amap MCP, fill these local `.env` values:

```bash
AMAP_MCP_URL=https://mcp.amap.com/mcp
AMAP_MCP_KEY=your_new_amap_key
MCP_BEARER_TOKEN=

RESTAURANT_PROVIDER=dianping
BROWSER_HARNESS_EXECUTABLE=browser-harness
```

The Amap key is optional only when it is already embedded in `AMAP_MCP_URL`. Do not commit real keys or bearer tokens. The agent discovers the tools exposed by the MCP server at runtime; this project does not hard-code provider-specific tool names.

When Amap MCP is configured, the application business client can search a place, load its POI details and coordinates, query driving/transit routes, generate a taxi URI, and normalize subway lines and route durations into `RouteInfo`. The Amap taxi tool returns a launch URI rather than a minute estimate, so the current taxi minute field uses the driving duration returned for the same origin and destination.

When a search request includes an `origin`, the service enriches every Dianping result with Amap route data in sequence: place lookup, driving route, taxi estimate reference, public-transit duration, and subway/bus lines. A route failure is stored on that restaurant as `route_error` instead of discarding the restaurant result.

## Run

```bash
uv run uvicorn restaurant_agent.api:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Chat request:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H 'content-type: application/json' \
  -d '{
    "user_id": "user-1",
    "message": "帮我找一家适合晚餐的意大利餐厅"
  }'
```

The response is platform-neutral:

```json
{
  "conversation_id": "generated-id",
  "message": "...",
  "recommendations": []
}
```

## Test

```bash
uv run pytest -q
python -m compileall src
```

The offline test suite does not call OpenAI or an external restaurant service.
