from __future__ import annotations

import json
from typing import Any

from agents import GuardrailFunctionOutput
from agents.decorators import input_guardrail, output_guardrail

from restaurant_agent.domain.contracts import ChatResponse


def _payload(input_value: Any) -> dict[str, Any] | None:
    if isinstance(input_value, list) and input_value:
        last_item = input_value[-1]
        if isinstance(last_item, dict):
            input_value = last_item.get("content")
    if isinstance(input_value, list):
        input_value = "".join(
            item.get("text", "")
            for item in input_value
            if isinstance(item, dict)
        )
    if not isinstance(input_value, str):
        return None
    try:
        value = json.loads(input_value)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


@input_guardrail(name="restaurant_workflow_input", run_in_parallel=False)
async def restaurant_input_guardrail(
    context: Any, agent: Any, input: Any
) -> GuardrailFunctionOutput:
    """Block malformed workflow payloads before the model can call tools."""

    payload = _payload(input)
    if payload is None:
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={"reason": "invalid_workflow_payload"},
        )

    recognized = payload.get("recognized_intent") or {}
    intents = set(recognized.get("intents") or [])
    if "route_query" in intents and not all(
        (recognized.get("route_origin"), recognized.get("route_destination"))
    ):
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={"reason": "route_endpoints_required"},
        )

    return GuardrailFunctionOutput(tripwire_triggered=False, output_info=None)


@output_guardrail(name="restaurant_response_output")
async def restaurant_output_guardrail(
    context: Any, agent: Any, agent_output: Any
) -> GuardrailFunctionOutput:
    """Ensure the final response is typed and contains a usable message."""

    valid = isinstance(agent_output, ChatResponse) and bool(agent_output.message.strip())
    return GuardrailFunctionOutput(
        tripwire_triggered=not valid,
        output_info=None if valid else {"reason": "empty_or_untyped_response"},
    )
