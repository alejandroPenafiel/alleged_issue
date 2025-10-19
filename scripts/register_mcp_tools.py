"""Register MCP tools with the ElizaOS API dynamically."""
from __future__ import annotations

import argparse
import asyncio
import os
from typing import Iterable

import httpx
import yaml


async def register_tools(api_base: str, registry_path: str) -> None:
    async with httpx.AsyncClient(base_url=api_base, timeout=10.0) as client:
        with open(registry_path, "r", encoding="utf-8") as handle:
            registry = yaml.safe_load(handle) or {}
        tools: Iterable[dict] = registry.get("tools", [])
        for tool in tools:
            payload = {
                "name": tool["name"],
                "endpoint": tool["endpoint"],
                "transport": tool.get("transport", "http"),
            }
            response = await client.post("/api/tools", json=payload)
            response.raise_for_status()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register MCP tools with ElizaOS")
    parser.add_argument("--api-base", default=os.getenv("ELIZA_API_BASE", "http://eliza:3000"))
    parser.add_argument("--registry", default=os.getenv("MCP_REGISTRY_PATH", "/app/config/mcp_endpoints.yml"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(register_tools(args.api_base, args.registry))
