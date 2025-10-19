"""Event-driven websocket consumer for the agent platform."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from typing import Any, Dict

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from redis.asyncio import Redis
import websockets

from tasks import celery_app, process_datapoint

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger("python-engine")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ENGINE_CHANNEL = os.getenv("ENGINE_CHANNEL", "engine:events")
WEBSOCKET_URL = os.getenv("ENGINE_WEBSOCKET_URL", "ws://example.com/stream")


class EngineEvent(BaseModel):
    """Validated structure for inbound websocket events."""

    source: str = Field(..., description="Identifier for the event producer")
    payload: Dict[str, Any] = Field(default_factory=dict)
    sequence: int | None = Field(default=None)


async def publish(redis: Redis, channel: str, message: Dict[str, Any]) -> None:
    """Publish a message to Redis pub/sub and store it as the latest snapshot."""
    encoded = json.dumps(message)
    await redis.publish(channel, encoded)
    await redis.set(f"{channel}:latest", encoded)
    LOGGER.debug("Published event to %s", channel)


async def handle_event(redis: Redis, event: EngineEvent) -> None:
    """Dispatch work for an EngineEvent."""
    LOGGER.info("Processing event from %s", event.source)
    payload = event.payload | {"source": event.source, "sequence": event.sequence}

    # Send async task through Celery.
    process_datapoint.delay(payload)

    # Notify downstream listeners via Redis pub/sub.
    await publish(redis, ENGINE_CHANNEL, payload)


async def keepalive(session: aiohttp.ClientSession) -> None:
    """Emit periodic keepalive pings to the websocket server."""
    while True:
        await asyncio.sleep(25)
        try:
            async with session.get(os.getenv("ENGINE_HEALTHCHECK_URL", "http://localhost/health")) as response:
                LOGGER.debug("Engine keepalive status: %s", response.status)
        except Exception as exc:  # noqa: BLE001
            LOGGER.debug("Keepalive probe failed: %s", exc)


async def event_loop() -> None:
    """Main consumer loop that ingests websocket messages."""
    redis = Redis.from_url(REDIS_URL)
    async with redis:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            LOGGER.info("Connected to upstream websocket %s", WEBSOCKET_URL)
            async for message in websocket:
                try:
                    payload = json.loads(message)
                    event = EngineEvent(**payload)
                except (json.JSONDecodeError, ValidationError) as exc:
                    LOGGER.warning("Discarding malformed event: %s", exc)
                    continue
                await handle_event(redis, event)


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        keepalive_task = asyncio.create_task(keepalive(session))
        try:
            await event_loop()
        finally:
            keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive_task


if __name__ == "__main__":
    asyncio.run(main())
