"""Backward-compatible exports for infrastructure providers."""

from restaurant_agent.infrastructure.providers import (
    RestaurantSearchProvider,
    SampleRestaurantProvider,
)

__all__ = ["RestaurantSearchProvider", "SampleRestaurantProvider"]
