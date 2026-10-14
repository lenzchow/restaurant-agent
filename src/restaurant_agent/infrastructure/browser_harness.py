from __future__ import annotations

import asyncio
from collections.abc import Sequence
from urllib.parse import urlsplit


_ALLOWED_DIANYING_HOSTS = {"dianping.com", "www.dianping.com", "m.dianping.com"}


def validate_dianping_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in _ALLOWED_DIANYING_HOSTS:
        raise ValueError("browser-harness is restricted to Dianping URLs")


class SubprocessBrowserHarness:
    def __init__(
        self,
        *,
        executable: str = "browser-harness",
        timeout_seconds: float = 90,
        command_prefix: Sequence[str] = (),
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.command_prefix = tuple(command_prefix)

    async def run(self, script: str, *, target_url: str | None = None) -> str:
        if target_url:
            validate_dianping_url(target_url)
        process = await asyncio.create_subprocess_exec(
            *self.command_prefix,
            self.executable,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(script.encode("utf-8")),
            timeout=self.timeout_seconds,
        )
        if process.returncode:
            message = stderr.decode("utf-8", errors="replace")[-1000:]
            raise RuntimeError(f"browser-harness failed: {message}")
        return stdout.decode("utf-8", errors="replace")
