from __future__ import annotations

import pytest

from restaurant_agent.application.confirmation import ConfirmationManager
from restaurant_agent.contracts import ChatRequest


def test_confirmation_manager_stores_pending_operation_for_user() -> None:
    manager = ConfirmationManager()
    request = ChatRequest(user_id="user-1", message="帮我找一家日料")

    operation = manager.create(
        request,
        actions=["打开 Chrome", "访问大众点评", "读取餐厅信息"],
    )

    found = manager.find(request.conversation_id, request.user_id)
    assert found is not None
    assert found.operation_id == operation.operation_id
    assert found.actions == ["打开 Chrome", "访问大众点评", "读取餐厅信息"]


def test_confirmation_manager_approves_operation_once() -> None:
    manager = ConfirmationManager()
    request = ChatRequest(user_id="user-1", message="帮我找一家日料")
    manager.create(request, actions=["访问大众点评"])

    approved = manager.approve(request.conversation_id, request.user_id)

    assert approved is not None
    assert manager.find(request.conversation_id, request.user_id) is None


def test_confirmation_manager_rejects_unknown_operation() -> None:
    manager = ConfirmationManager()

    assert manager.reject("missing-conversation", "user-1") is None
