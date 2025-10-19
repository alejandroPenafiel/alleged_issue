from __future__ import annotations

import os
import sys

from redis import Redis


def main() -> int:
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = Redis.from_url(url)
        client.ping()
    except Exception as exc:  # noqa: BLE001
        print(f"Redis healthcheck failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
