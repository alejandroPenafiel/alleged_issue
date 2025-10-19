from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Iterable

import httpx

REGISTRY_PATH = Path(os.environ.get("MCP_ENDPOINTS_FILE", "/mcp/endpoints.json"))
ELIZA_API_URL = os.environ.get("ELIZA_API_URL", "http://eliza:3000/api/tools")
MAX_ATTEMPTS = int(os.environ.get("ELIZA_TOOL_ATTEMPTS", "20"))
ATTEMPT_DELAY = float(os.environ.get("ELIZA_TOOL_ATTEMPT_DELAY", "3"))


async def load_registry() -> Iterable[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


async def wait_for_eliza(client: httpx.AsyncClient) -> None:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = await client.get(f"{ELIZA_API_URL}/health")
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            if attempt == MAX_ATTEMPTS:
                raise
        await asyncio.sleep(ATTEMPT_DELAY)


async def register_tool(client: httpx.AsyncClient, tool: dict[str, Any]) -> None:
    payload = {
        "name": tool.get("name"),
        "displayName": tool.get("displayName", tool.get("name")),
        "endpoint": tool.get("endpoint"),
        "transport": tool.get("transport", "http"),
        "metadata": {
            "capabilities": tool.get("capabilities", []),
            "health": tool.get("health"),
        },
    }
    response = await client.post(ELIZA_API_URL, json=payload)
    response.raise_for_status()


async def main() -> None:
    registry = await load_registry()
    if not registry:
        print("No MCP tools discovered; skipping registration")
        return
    async with httpx.AsyncClient(timeout=10.0) as client:
        await wait_for_eliza(client)
        for tool in registry:
            try:
                await register_tool(client, tool)
                print(f"Registered {tool.get('name')}")
            except httpx.HTTPStatusError as exc:
                print(f"Failed to register {tool.get('name')}: {exc.response.text}")
            except httpx.HTTPError as exc:
                print(f"HTTP error registering {tool.get('name')}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
