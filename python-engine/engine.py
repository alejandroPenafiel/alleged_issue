"""Async WebSocket consumer that streams data into Redis and Celery."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import uuid
from contextlib import suppress
from dataclasses import dataclass

import redis.asyncio as redis
import websockets
from websockets.client import WebSocketClientProtocol

from celery_app import process_event
from mcp_client import MCPRegistry

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DATA_FEED_URL = os.getenv("DATA_FEED_URL", "ws://example.com/feed")
RESULT_CHANNEL = os.getenv("RESULT_CHANNEL", "engine.results")
CACHE_KEY = os.getenv("CACHE_KEY", "engine:last_result")


@dataclass
class EngineContext:
    redis_client: redis.Redis
    registry: MCPRegistry


async def fetch_registry() -> MCPRegistry:
    registry_path = os.getenv("TOOL_REGISTRY_PATH")
    return MCPRegistry.from_file(registry_path) if registry_path else MCPRegistry.default()


async def process_message(ctx: EngineContext, message: str) -> None:
    payload = json.loads(message)
    event_id = payload.get("id", str(uuid.uuid4()))
    result = {
        "id": event_id,
        "value": payload.get("value"),
        "source": payload.get("source", "feed"),
    }

    await ctx.redis_client.set(CACHE_KEY, json.dumps(result))
    await ctx.redis_client.publish(RESULT_CHANNEL, json.dumps(result))

    task = process_event.delay(result)
    await ctx.redis_client.hset("engine:tasks", task.id, json.dumps(result))

    for tool in ctx.registry.tools:
        await ctx.redis_client.rpush("engine:tool_notifications", json.dumps({
            "tool": tool.name,
            "endpoint": tool.endpoint,
            "event_id": event_id,
        }))


async def stream_events(ctx: EngineContext) -> None:
    try:
        async with websockets.connect(DATA_FEED_URL) as websocket:
            await consume_websocket(ctx, websocket)
    except OSError:
        await simulate_feed(ctx)


async def consume_websocket(ctx: EngineContext, websocket: WebSocketClientProtocol) -> None:
    async for message in websocket:
        await process_message(ctx, message)


async def simulate_feed(ctx: EngineContext) -> None:
    for index in range(3):
        payload = json.dumps({"id": str(uuid.uuid4()), "value": index, "source": "simulated"})
        await process_message(ctx, payload)
        await asyncio.sleep(1)


async def main() -> None:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    registry = await fetch_registry()
    await registry.warm_endpoints()
    ctx = EngineContext(redis_client=redis_client, registry=registry)

    stop_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, stop_event.set)  # type: ignore[arg-type]
        loop.add_signal_handler(signal.SIGTERM, stop_event.set)  # type: ignore[arg-type]
    except (NotImplementedError, RuntimeError):  # pragma: no cover - Windows/threads
        pass

    worker = asyncio.create_task(stream_events(ctx))
    stopper = asyncio.create_task(stop_event.wait())

    try:
        done, _ = await asyncio.wait({worker, stopper}, return_when=asyncio.FIRST_COMPLETED)
        if stopper in done:
            worker.cancel()
        else:
            stop_event.set()
    finally:
        for task in (worker, stopper):
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())
