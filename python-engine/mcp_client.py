"""Utilities for discovering and querying MCP endpoints."""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

import httpx
import yaml


@dataclass
class MCPTool:
    name: str
    endpoint: str
    transport: str = "http"


@dataclass
class MCPRegistry:
    tools: List[MCPTool]

    @classmethod
    def from_file(cls, path: str) -> "MCPRegistry":
        with open(path, "r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        tools = [MCPTool(**entry) for entry in payload.get("tools", [])]
        return cls(tools=tools)

    @classmethod
    def default(cls) -> "MCPRegistry":
        endpoints = os.getenv("DEFAULT_MCP_ENDPOINTS", "").split(",")
        tools = [
            MCPTool(name=f"tool_{index}", endpoint=endpoint.strip())
            for index, endpoint in enumerate(filter(None, endpoints))
        ]
        return cls(tools=tools)

    async def warm_endpoints(self) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            tasks = [self._warm_single(client, tool) for tool in self.tools]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _warm_single(self, client: httpx.AsyncClient, tool: MCPTool) -> None:
        try:
            await client.get(f"{tool.endpoint.rstrip('/')}/health")
        except httpx.HTTPError:
            # The endpoint might not expose health route; ignore.
            return


async def invoke_mcp_tool(tool: MCPTool, payload: dict) -> Optional[dict]:
    url = f"{tool.endpoint.rstrip('/')}/mcp"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else None


async def broadcast_to_registry(registry: MCPRegistry, payload: dict) -> List[dict]:
    tasks = [invoke_mcp_tool(tool, payload) for tool in registry.tools]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    output: List[dict] = []
    for item in results:
        if isinstance(item, dict):
            output.append(item)
    return output
