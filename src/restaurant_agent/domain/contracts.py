from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from restaurant_agent.intents.models import IntentType


class ConfirmationDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ResponseStatus(StrEnum):
    COMPLETED = "completed"
    CONFIRMATION_REQUIRED = "confirmation_required"
    REJECTED = "rejected"


class RouteInfo(BaseModel):
    origin: str
    destination: str
    driving_distance_km: float | None = Field(default=None, ge=0)
    taxi_duration_minutes: int | None = Field(default=None, ge=0)
    transit_duration_minutes: int | None = Field(default=None, ge=0)
    matched_address: str | None = None
    taxi_uri: str | None = None
    subway_lines: list[str] = Field(default_factory=list)
    bus_lines: list[str] = Field(default_factory=list)
    requested_modes: list[str] = Field(default_factory=list)
    unsupported_modes: list[str] = Field(default_factory=list)
    queried_at: str | None = None


class Review(BaseModel):
    content: str
    rating: float | None = Field(default=None, ge=0, le=5)
    tags: list[str] = Field(default_factory=list)
    created_at: str | None = None


class Restaurant(BaseModel):
    name: str
    cuisine: str
    address: str
    price_per_person: float = Field(ge=0)
    distance_km: float = Field(ge=0)
    recommended_dishes: list[str] = Field(default_factory=list)
    recommended_dish_images: list[str] = Field(default_factory=list)
    recommendation_note: str | None = None
    recommendation_image_note: str | None = None
    opening_hours: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    review_summary: str | None = None
    review_highlights: list[str] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)
    review_count: int | None = Field(default=None, ge=0)
    review_tags: list[str] = Field(default_factory=list)
    source_url: str | None = None
    source_fetched_at: str | None = None
    route: RouteInfo | None = None
    route_error: str | None = None


class RestaurantSearchInput(BaseModel):
    city: str | None = None
    location: str | None = None
    cuisine: str | None = None
    sort: str = "smart"
    max_budget: float | None = Field(default=None, ge=0)
    max_distance_km: float | None = Field(default=None, ge=0)
    party_size: int | None = Field(default=None, ge=1)
    page: int = Field(default=1, ge=1, le=50)
    limit: int = Field(default=10, ge=1, le=20)


class ChatRequest(BaseModel):
    conversation_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    message: str
    platform: str | None = None
    confirmation: ConfirmationDecision | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    status: ResponseStatus = ResponseStatus.COMPLETED
    operation_id: str | None = None
    requires_confirmation: bool = False
    requested_actions: list[str] = Field(default_factory=list)
    intent: IntentType | None = None
    intents: list[IntentType] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
    conflicts: list[str] = Field(default_factory=list)
    search_conditions: RestaurantSearchInput | None = None
    condition_candidates: dict[str, list[object]] = Field(default_factory=dict)
    search_confirmation_required: bool = False
    recommendations: list[Restaurant] = Field(default_factory=list)
    route: RouteInfo | None = None
