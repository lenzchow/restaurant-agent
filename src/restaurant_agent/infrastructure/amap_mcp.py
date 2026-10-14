from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams
from pydantic import BaseModel, SecretStr


class AmapMCPConfig(BaseModel):
    """Configuration for the remote Amap Streamable HTTP MCP server."""

    url: str | None = None
    api_key: SecretStr | None = None
    bearer_token: SecretStr | None = None

    @property
    def resolved_url(self) -> str | None:
        if not self.url:
            return None
        if not self.api_key or "key" in dict(parse_qsl(urlsplit(self.url).query)):
            return self.url

        parts = urlsplit(self.url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        query.append(("key", self.api_key.get_secret_value()))
        return urlunsplit(parts._replace(query=urlencode(query)))

    @property
    def headers(self) -> dict[str, str]:
        if not self.bearer_token:
            return {}
        return {"Authorization": f"Bearer {self.bearer_token.get_secret_value()}"}


def create_amap_mcp_server(config: AmapMCPConfig) -> MCPServerStreamableHttp | None:
    resolved_url = config.resolved_url
    if not resolved_url:
        return None

    params: MCPServerStreamableHttpParams = {"url": resolved_url, "headers": config.headers}
    return MCPServerStreamableHttp(
        params=params,
        name="Amap MCP",
        cache_tools_list=False,
        client_session_timeout_seconds=30,
    )
