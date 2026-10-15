"""Backward-compatible exports for the domain contracts."""

from restaurant_agent.domain.contracts import (
    ChatRequest,
    ChatResponse,
    ConditionCandidates,
    ConfirmationDecision,
    Restaurant,
    RestaurantSearchInput,
    Review,
    ResponseStatus,
    RouteInfo,
    TransitOption,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ConditionCandidates",
    "ConfirmationDecision",
    "Restaurant",
    "RestaurantSearchInput",
    "Review",
    "ResponseStatus",
    "RouteInfo",
    "TransitOption",
]
