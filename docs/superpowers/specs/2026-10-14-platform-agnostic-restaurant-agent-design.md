# Platform-Agnostic Restaurant Agent Design

## Goal

Build a first working restaurant-finding agent that can be called through a generic HTTP API and can later be connected to Feishu, a web UI, Slack, or another platform without changing the restaurant-agent core.

## Scope

- Accept a natural-language restaurant request through FastAPI.
- Validate transport data with Pydantic.
- Run one OpenAI Agent through the Agents SDK.
- Use the Responses API-backed Agents SDK runtime for model inference and tool calls.
- Expose a typed restaurant-search tool with a replaceable provider boundary.
- Return a stable, platform-neutral response contract.
- Include deterministic local sample data so the project can be tested without a restaurant API key.

## Non-goals

- No Feishu-specific webhook or message formatting in the first version.
- No real map, review, reservation, or payment integration yet.
- No multi-agent orchestration yet.
- No persistent database or conversation store yet.

## Architecture

```text
HTTP transport (FastAPI)
        |
        v
Pydantic ChatRequest / ChatResponse
        |
        v
Restaurant Agent service
        |
        v
OpenAI Agents SDK -> Responses API
        |
        v
RestaurantSearchProvider protocol
        |
        v
Local sample provider (MVP) / future external provider
```

The transport layer knows only the request and response contracts. The agent knows only the restaurant search tool contract. A future platform adapter converts platform-specific messages to `ChatRequest` and converts `ChatResponse` back to that platform's format.

## Contracts

`ChatRequest` contains `conversation_id`, `user_id`, `message`, and an optional `platform` label. `ChatResponse` contains `conversation_id`, `message`, and a list of structured restaurant recommendations.

The search tool accepts location, cuisine, maximum budget per person, party size, and limit. Missing filters are allowed. The provider returns typed `Restaurant` records.

## Error handling

- FastAPI returns HTTP 422 for malformed request bodies.
- The agent service returns a controlled HTTP 500 response for unexpected model/provider failures without exposing secrets.
- Provider failures are represented internally as exceptions and are covered by service tests.
- The API does not claim that a restaurant is open, available, or current until a live provider is added.

## Testing

- Contract tests validate request defaults and response serialization.
- Provider tests validate filtering and result limits against sample data.
- API tests mock the agent service and verify the endpoint contract without network access.
- A separate smoke command is documented for a real `OPENAI_API_KEY`; it is not part of the offline test suite.
