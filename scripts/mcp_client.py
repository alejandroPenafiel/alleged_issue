"""Utility helpers for interacting with MCP endpoints programmatically."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable

import aiohttp


@dataclass
class MCPService:
    name: str
    url: str


class MCPClient:
    """Minimal async client for JSON-RPC based MCP services."""

    def __init__(self, service: MCPService) -> None:
        self.service = service

    async def _request(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": method,
            "method": method,
            "params": params or {},
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.service.url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def capabilities(self) -> Dict[str, Any]:
        return await self._request("capabilities/list")

    async def list_tools(self) -> Dict[str, Any]:
        return await self._request("tools/list")

    async def call_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        return await self._request("tools/call", {"name": tool_name, "arguments": kwargs})


async def discover(endpoints: Iterable[MCPService]) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for service in endpoints:
        client = MCPClient(service)
        try:
            capabilities = await client.capabilities()
            results[service.name] = {
                "status": "ready",
                "capabilities": capabilities.get("result"),
            }
        except Exception as exc:  # noqa: BLE001
            results[service.name] = {"status": "error", "error": str(exc)}
    return results


async def main() -> None:
    services = [
        MCPService(name="serena", url="http://localhost:9121/mcp"),
        MCPService(name="context7", url="http://localhost:7070/mcp"),
    ]
    registry = await discover(services)
    print(json.dumps(registry, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
