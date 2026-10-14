from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from restaurant_agent.domain.contracts import ChatRequest


@dataclass(frozen=True)
class PendingOperation:
    operation_id: str
    request: ChatRequest
    actions: list[str]


class ConfirmationManager:
    def __init__(self) -> None:
        self._pending: dict[tuple[str, str], PendingOperation] = {}

    def create(self, request: ChatRequest, *, actions: list[str]) -> PendingOperation:
        operation = PendingOperation(
            operation_id=str(uuid4()),
            request=request,
            actions=actions,
        )
        self._pending[(request.conversation_id, request.user_id)] = operation
        return operation

    def find(self, conversation_id: str, user_id: str) -> PendingOperation | None:
        return self._pending.get((conversation_id, user_id))

    def approve(self, conversation_id: str, user_id: str) -> PendingOperation | None:
        return self._pending.pop((conversation_id, user_id), None)

    def reject(self, conversation_id: str, user_id: str) -> PendingOperation | None:
        return self._pending.pop((conversation_id, user_id), None)
