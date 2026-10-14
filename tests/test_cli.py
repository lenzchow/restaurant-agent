from restaurant_agent.cli import format_cli_response
from restaurant_agent.domain.contracts import ChatResponse, RestaurantSearchInput


def test_cli_formats_search_condition_preview() -> None:
    text = format_cli_response(
        ChatResponse(
            conversation_id="c",
            message="请确认",
            search_conditions=RestaurantSearchInput(city="北京"),
            search_confirmation_required=True,
        )
    )

    assert "北京" in text
    assert "请确认" in text
