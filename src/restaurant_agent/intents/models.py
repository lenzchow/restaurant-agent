from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class IntentType(StrEnum):
    RESTAURANT_RECOMMENDATION = "restaurant_recommendation"
    RESTAURANT_DETAILS_QUERY = "restaurant_details_query"
    DISH_RECOMMENDATION = "dish_recommendation"
    CUISINE_QUERY = "cuisine_query"
    ROUTE_QUERY = "route_query"
    OPENING_HOURS_QUERY = "opening_hours_query"
    RATING_REVIEW_QUERY = "rating_review_query"
    REVIEW_SUMMARY_QUERY = "review_summary_query"
    GENERAL_CHAT = "general_chat"


class IntentResult(BaseModel):
    intent: IntentType
    intents: list[IntentType] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
    conflicts: list[str] = Field(default_factory=list)
    route_origin: str | None = None
    route_destination: str | None = None
