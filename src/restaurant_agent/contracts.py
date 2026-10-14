"""Backward-compatible exports for the domain contracts."""

from restaurant_agent.domain.contracts import (
    ChatRequest,
    ChatResponse,
    ConfirmationDecision,
    Restaurant,
    RestaurantSearchInput,
    ResponseStatus,
    RouteInfo,
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ConfirmationDecision",
    "Restaurant",
    "RestaurantSearchInput",
    "ResponseStatus",
    "RouteInfo",
]
