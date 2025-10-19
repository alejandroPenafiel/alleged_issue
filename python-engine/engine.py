"""Async WebSocket engine that distributes work via Redis and Celery.

The engine consumes a WebSocket stream, enriches each event, publishes an
announcement on Redis pub/sub, and dispatches a Celery task for heavier
background processing.  It also keeps track of the available MCP tools so other
services can discover them at runtime.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from typing import Any, Dict, Optional

import redis.asyncio as redis
import websockets
from tenacity import retry, stop_after_delay, wait_exponential

from celery_app import process_event
from mcp_client import MCPClient, MCPServer, discover_servers

logging.basicConfig(level=os.getenv("ENGINE_LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger("python-engine")


class Engine:
    def __init__(self) -> None:
        self.websocket_url = os.getenv("WEBSOCKET_URL", "wss://echo.websocket.events")
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.pubsub_channel = os.getenv("ENGINE_PUBSUB_CHANNEL", "engine.events")
        self.stream_key = os.getenv("ENGINE_STREAM_KEY", "engine:events")
        self.task_queue = os.getenv("ENGINE_TASK_QUEUE", "engine.tasks")
        self.mcp_registry = os.getenv("MCP_SERVICE_REGISTRY", "http://registry:8500/registry.json")
        self._redis: Optional[redis.Redis] = None
        self._client = MCPClient()
        self._mcp_servers: Dict[str, MCPServer] = {}

    async def start(self) -> None:
        LOGGER.info("Starting engine. WebSocket=%s Redis=%s", self.websocket_url, self.redis_url)
        self._redis = redis.Redis.from_url(self.redis_url, decode_responses=True)
        await self.refresh_mcp_servers()
        stop_event = asyncio.Event()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_event.set)

        consumer_task = asyncio.create_task(self.consume_websocket(stop_event))
        refresher_task = asyncio.create_task(self.refresh_mcp_periodically(stop_event))

        await stop_event.wait()
        LOGGER.info("Shutdown signal received. Waiting for tasks to finish...")
        consumer_task.cancel()
        refresher_task.cancel()
        await asyncio.gather(consumer_task, refresher_task, return_exceptions=True)
        await self._client.close()
        if self._redis:
            await self._redis.close()

    async def refresh_mcp_servers(self) -> None:
        try:
            servers = await discover_servers(self.mcp_registry)
            if servers:
                self._mcp_servers = servers
                LOGGER.info("Discovered MCP servers: %s", list(servers.keys()))
            else:
                LOGGER.warning("No MCP servers discovered at %s", self.mcp_registry)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Failed to refresh MCP registry: %s", exc)

    async def refresh_mcp_periodically(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await asyncio.sleep(60)
            await self.refresh_mcp_servers()

    async def consume_websocket(self, stop_event: asyncio.Event) -> None:
        @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_delay(300))
        async def _connect() -> websockets.WebSocketClientProtocol:
            LOGGER.info("Connecting to WebSocket %s", self.websocket_url)
            return await websockets.connect(self.websocket_url, ping_interval=20)

        while not stop_event.is_set():
            try:
                async with await _connect() as websocket:
                    async for message in websocket:
                        payload = self.parse_message(message)
                        await self.process_payload(payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.warning("WebSocket disconnected (%s). Retrying...", exc)
                await asyncio.sleep(5)

    async def process_payload(self, payload: Dict[str, Any]) -> None:
        if self._redis is None:
            raise RuntimeError("Redis connection has not been initialized")
        LOGGER.debug("Received payload: %s", payload)
        payload["queue"] = self.task_queue

        await self._redis.xadd(self.stream_key, fields={"event": json.dumps(payload)})
        await self._redis.publish(self.pubsub_channel, json.dumps(payload))

        process_event.apply_async(args=[payload], queue=self.task_queue)

        await self.invoke_default_mcp_tool(payload)

    async def invoke_default_mcp_tool(self, payload: Dict[str, Any]) -> None:
        if not self._mcp_servers:
            return
        server = next(iter(self._mcp_servers.values()))
        try:
            response = await self._client.invoke_tool(server, "ingest_event", payload)
            LOGGER.debug("MCP response from %s: %s", server.name, response)
        except Exception as exc:
            LOGGER.debug("MCP invocation failed for %s: %s", server.name, exc)

    def parse_message(self, message: str) -> Dict[str, Any]:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            data = {"raw": message}
        data.setdefault("source", "websocket")
        return data


def main() -> None:
    asyncio.run(Engine().start())


if __name__ == "__main__":
    main()
