"""Lightweight client helpers for interacting with HTTP/SSE based MCP servers.

The helpers cover the most common operations needed by the engine:
  * Discovering capabilities via the `/mcp` endpoint
  * Establishing a Server-Sent Event (SSE) stream for push updates
  * Invoking JSON based tools exposed by the server

These utilities are intentionally dependency-light so they can run from
background workers or ad-hoc scripts.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp

LOGGER = logging.getLogger(__name__)


@dataclass
class MCPServer:
    name: str
    base_url: str

    @property
    def mcp_url(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def sse_url(self) -> str:
        return f"{self.mcp_url}/sse"


class MCPClient:
    def __init__(self, session: Optional[aiohttp.ClientSession] = None) -> None:
        self._session = session

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def fetch_capabilities(self, server: MCPServer) -> Dict[str, Any]:
        session = await self._get_session()
        async with session.get(server.mcp_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            data = await resp.json()
            LOGGER.debug("Fetched capabilities from %s: %s", server.name, data)
            return data

    async def invoke_tool(
        self,
        server: MCPServer,
        tool: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        session = await self._get_session()
        request_body = {"tool": tool, "payload": payload}
        async with session.post(
            server.mcp_url,
            data=json.dumps(request_body),
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            LOGGER.debug("Invoked tool %s on %s: %s", tool, server.name, data)
            return data

    async def stream_events(self, server: MCPServer) -> AsyncIterator[Dict[str, Any]]:
        session = await self._get_session()
        async with session.get(server.sse_url) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                if not line:
                    continue
                decoded = line.decode().strip()
                if not decoded or decoded.startswith(":"):
                    continue
                if decoded.startswith("data:"):
                    payload = decoded.split("data:", 1)[1].strip()
                    try:
                        yield json.loads(payload)
                    except json.JSONDecodeError:
                        LOGGER.debug("Received non-JSON SSE payload from %s: %s", server.name, payload)
                        yield {"raw": payload}

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()


async def discover_servers(registry_url: str) -> Dict[str, MCPServer]:
    async with aiohttp.ClientSession() as session:
        async with session.get(registry_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            resp.raise_for_status()
            data = await resp.json()
    servers = {
        name: MCPServer(name=name, base_url=url)
        for name, url in data.get("endpoints", {}).items()
    }
    return servers


async def main(registry_url: str) -> None:
    logging.basicConfig(level=logging.INFO)
    servers = await discover_servers(registry_url)
    client = MCPClient()
    try:
        for name, server in servers.items():
            capabilities = await client.fetch_capabilities(server)
            LOGGER.info("%s capabilities: %s", name, capabilities.keys())
    finally:
        await client.close()


if __name__ == "__main__":
    import os

    url = os.getenv("MCP_SERVICE_REGISTRY", "http://localhost:8500/registry.json")
    asyncio.run(main(url))
