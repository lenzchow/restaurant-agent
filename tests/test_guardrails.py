from __future__ import annotations

import json

import pytest
from agents import Agent, RunContextWrapper

from restaurant_agent.application.guardrails import (
    restaurant_input_guardrail,
    restaurant_output_guardrail,
)
from restaurant_agent.contracts import ChatResponse, Restaurant


@pytest.mark.asyncio
async def test_input_guardrail_blocks_route_workflow_without_endpoints() -> None:
    result = await restaurant_input_guardrail.run(
        Agent(name="test-agent"),
        json.dumps(
            {
                "recognized_intent": {
                    "intents": ["route_query"],
                    "route_origin": None,
                    "route_destination": None,
                }
            }
        ),
        RunContextWrapper(None),
    )

    assert result.output.tripwire_triggered is True


@pytest.mark.asyncio
async def test_input_guardrail_allows_valid_route_workflow() -> None:
    result = await restaurant_input_guardrail.run(
        Agent(name="test-agent"),
        json.dumps(
            {
                "recognized_intent": {
                    "intents": ["route_query"],
                    "route_origin": "学校",
                    "route_destination": "餐厅",
                }
            }
        ),
        RunContextWrapper(None),
    )

    assert result.output.tripwire_triggered is False


@pytest.mark.asyncio
async def test_output_guardrail_blocks_empty_agent_message() -> None:
    result = await restaurant_output_guardrail.run(
        RunContextWrapper(None),
        Agent(name="test-agent"),
        ChatResponse(conversation_id="c", message="   "),
    )

    assert result.output.tripwire_triggered is True


@pytest.mark.asyncio
async def test_output_guardrail_blocks_unlabelled_recommendation_source() -> None:
    result = await restaurant_output_guardrail.run(
        RunContextWrapper(None),
        Agent(name="test-agent"),
        ChatResponse(
            conversation_id="c",
            message="推荐一家餐厅",
            recommendations=[
                Restaurant(
                    name="样例店",
                    cuisine="日料",
                    address="地址",
                    price_per_person=100,
                    distance_km=1,
                )
            ],
        ),
    )

    assert result.output.tripwire_triggered is True
