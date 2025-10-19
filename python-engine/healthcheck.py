"""Simple healthcheck script ensuring Redis connectivity."""
from __future__ import annotations

import asyncio
import os

import redis.asyncio as redis


async def main() -> int:
    client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
    try:
        pong = await client.ping()
        return 0 if pong else 1
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
