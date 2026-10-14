"""Backward-compatible exports for the Amap MCP integration."""

from restaurant_agent.infrastructure.amap_mcp import (
    AmapMCPConfig,
    create_amap_mcp_server,
)

__all__ = ["AmapMCPConfig", "create_amap_mcp_server"]
