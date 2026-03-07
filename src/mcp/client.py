"""
MCP Client Manager — integrates MultiServerMCPClient with config-driven
hot-reloadable MCP server tool lists.

Reads extensions_config.json for the MCP server manifest and exposes
get_mcp_tools() to return a list of LangChain-compatible tools.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool

# Lazy import to avoid hard failure if langchain-mcp-adapters is not yet installed
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    MultiServerMCPClient = None  # type: ignore

EXTENSIONS_CONFIG_PATH = Path(
    os.environ.get("EXTENSIONS_CONFIG_PATH", "extensions_config.json")
)

# Global singleton
_client_manager: "MCPClientManager | None" = None


class MCPClientManager:
    """
    Manages a MultiServerMCPClient instance backed by extensions_config.json.

    Supports hot-reloading: calling reload() re-reads the config file and
    rebuilds the client with the new server list.
    """

    def __init__(self, config_path: Path = EXTENSIONS_CONFIG_PATH) -> None:
        self._config_path = config_path
        self._client: Any = None
        self._tools: list[BaseTool] = []
        self._load()

    def _load(self) -> None:
        """Read config and (re)create the MCP client."""
        if not self._config_path.exists():
            self._tools = []
            return

        with open(self._config_path) as f:
            config = json.load(f)

        servers = config.get("mcp_servers", [])
        enabled_servers = [s for s in servers if s.get("enabled", False)]

        if not enabled_servers or not _MCP_AVAILABLE:
            self._tools = []
            return

        # Build server config dict for MultiServerMCPClient
        server_configs: dict[str, Any] = {}
        for srv in enabled_servers:
            name = srv["name"]
            transport = srv.get("transport", "stdio")
            entry: dict[str, Any] = {"transport": transport}
            if transport == "stdio":
                entry["command"] = srv["command"]
                entry["args"] = srv.get("args", [])
                env = srv.get("env", {})
                # Resolve env vars
                entry["env"] = {
                    k: os.environ.get(v.lstrip("$"), v)
                    for k, v in env.items()
                }
            elif transport in ("http", "sse"):
                entry["url"] = srv["url"]
            server_configs[name] = entry

        self._client = MultiServerMCPClient(server_configs)

    def get_tools(self) -> list[BaseTool]:
        """Return current list of MCP tools."""
        return list(self._tools)

    def reload(self) -> None:
        """Hot-reload the config and rebuild the MCP client."""
        self._load()


def get_mcp_tools() -> list[BaseTool]:
    """
    Module-level convenience function: return MCP tools from the global manager.
    Lazily initialises MCPClientManager on first call.
    """
    global _client_manager
    if _client_manager is None:
        _client_manager = MCPClientManager()
    return _client_manager.get_tools()
