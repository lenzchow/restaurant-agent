from __future__ import annotations

import pytest

from restaurant_agent.infrastructure.browser_harness import (
    SubprocessBrowserHarness,
    validate_dianping_url,
)


def test_validate_dianping_url_accepts_allowed_hosts() -> None:
    validate_dianping_url("https://www.dianping.com/shop/abc")
    validate_dianping_url("https://m.dianping.com/shop/abc")


def test_validate_dianping_url_rejects_other_hosts() -> None:
    with pytest.raises(ValueError):
        validate_dianping_url("https://example.com/shop/abc")


def test_subprocess_harness_keeps_command_configuration_explicit() -> None:
    harness = SubprocessBrowserHarness(executable="browser-harness")

    assert harness.executable == "browser-harness"
