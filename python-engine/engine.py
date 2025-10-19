from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import string
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict, Iterable, List

import httpx
import websockets
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from celery_app import process_payload
from mcp_registry import MCPService, load_registry

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
LOGGER = logging.getLogger("python-engine")


class EngineConfig(BaseModel):
    websocket_url: str = Field(default="ws://localhost:8765/stream")
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_channel: str = Field(default="engine:events")
    redis_stream: str = Field(default="engine:stream")
    result_ttl: int = Field(default=3600)
    enable_celery: bool = Field(default=True)
    mcp_registry_path: str | None = Field(default=None)

    @classmethod
    def from_env(cls) -> "EngineConfig":
        return cls(
            websocket_url=os.getenv("WEBSOCKET_URL", cls.model_fields["websocket_url"].default),
            redis_url=os.getenv("REDIS_URL", cls.model_fields["redis_url"].default),
            redis_channel=os.getenv("REDIS_CHANNEL", cls.model_fields["redis_channel"].default),
            redis_stream=os.getenv("REDIS_STREAM", cls.model_fields["redis_stream"].default),
            result_ttl=int(os.getenv("ENGINE_RESULT_TTL", "3600")),
            enable_celery=os.getenv("ENGINE_ENABLE_CELERY", "true").lower() == "true",
            mcp_registry_path=os.getenv("MCP_ENDPOINTS_FILE"),
        )


class IncomingPayload(BaseModel):
    correlation_id: str | None = None
    value: float = 0.0
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class EngineResult(BaseModel):
    record_id: str
    value: float
    normalized: float
    tags: List[str]
    metadata: Dict[str, str]
    mcp_services: List[str]


async def discover_mcp_services(registry_path: str | None) -> List[MCPService]:
    services = load_registry(registry_path)
    if services:
        LOGGER.info("discovered %d MCP services", len(services))
    else:
        LOGGER.warning("no MCP services discovered from %s", registry_path)
    return services


@asynccontextmanager
async def redis_connection(url: str) -> AsyncGenerator[Redis, None]:
    client = Redis.from_url(url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def ensure_stream(client: Redis, stream_name: str) -> None:
    exists = await client.exists(stream_name)
    if not exists:
        await client.xadd(stream_name, {"message": "stream-initialized"})
        LOGGER.info("initialized redis stream %s", stream_name)


def _random_id(prefix: str = "evt") -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


async def websocket_stream(url: str) -> AsyncGenerator[IncomingPayload, None]:
    LOGGER.info("connecting to websocket %s", url)
    try:
        async with websockets.connect(url) as socket:
            async for message in socket:
                payload = IncomingPayload.model_validate_json(message)
                yield payload
    except (OSError, websockets.WebSocketException) as exc:
        LOGGER.error("websocket connection failed (%s), switching to synthetic data", exc)
        async for payload in synthetic_stream():
            yield payload


async def synthetic_stream() -> AsyncGenerator[IncomingPayload, None]:
    LOGGER.info("starting synthetic data stream")
    while True:
        await asyncio.sleep(5)
        yield IncomingPayload(
            correlation_id=_random_id("synthetic"),
            value=random.uniform(0, 100),
            tags=["synthetic", "fallback"],
            metadata={"source": "synthetic"},
        )


async def persist_result(client: Redis, stream: str, channel: str, result: EngineResult) -> None:
    payload = result.model_dump()
    await client.set(result.record_id, json.dumps(payload), ex=3600)
    await client.xadd(stream, payload)
    await client.publish(channel, json.dumps(payload))
    LOGGER.info("persisted result %s", result.record_id)


async def trigger_celery(payload: IncomingPayload) -> None:
    process_payload.delay(payload.model_dump())


async def ping_services(services: Iterable[MCPService]) -> None:
    timeout = httpx.Timeout(3.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for service in services:
            if not service.health:
                continue
            try:
                response = await client.get(service.health)
                LOGGER.info(
                    "MCP service %s health %s", service.name, response.status_code
                )
            except httpx.HTTPError as exc:
                LOGGER.warning("MCP service %s health check failed: %s", service.name, exc)


async def engine_main() -> None:
    config = EngineConfig.from_env()
    services = await discover_mcp_services(config.mcp_registry_path)
    async with redis_connection(config.redis_url) as redis_client:
        await ensure_stream(redis_client, config.redis_stream)
        if services:
            await ping_services(services)
        async for payload in websocket_stream(config.websocket_url):
            normalized = round(payload.value / 100.0, 4)
            record_id = payload.correlation_id or _random_id("event")
            result = EngineResult(
                record_id=record_id,
                value=payload.value,
                normalized=normalized,
                tags=sorted(set(payload.tags + ["processed"])),
                metadata=payload.metadata,
                mcp_services=[service.endpoint for service in services],
            )
            await persist_result(redis_client, config.redis_stream, config.redis_channel, result)
            if config.enable_celery:
                await trigger_celery(payload)


if __name__ == "__main__":
    try:
        asyncio.run(engine_main())
    except KeyboardInterrupt:
        LOGGER.info("engine shutdown requested")
