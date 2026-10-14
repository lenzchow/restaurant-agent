from __future__ import annotations

import pytest


@pytest.fixture
def sample_request_payload() -> dict[str, str]:
    return {
        "conversation_id": "conversation-test",
        "user_id": "user-test",
        "message": "Find an Italian restaurant for dinner",
    }
