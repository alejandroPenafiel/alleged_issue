"""Generate a registry file by probing running MCP containers."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List

import docker
import yaml


DEFAULT_SERVICES = {
    "serena": ("mcp-serena", 9121),
    "redis-explorer": ("mcp-redis", 8080),
    "context7": ("context7-mcp", 7070),
}


def discover(services: dict[str, tuple[str, int]]) -> List[dict]:
    client = docker.from_env()
    endpoints: List[dict] = []
    for name, (container_name, port) in services.items():
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            continue
        if container.status != "running":
            continue
        endpoints.append(
            {
                "name": name,
                "endpoint": f"http://{container_name}:{port}",
                "transport": "http",
            }
        )
    return endpoints


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover MCP endpoints from Docker")
    parser.add_argument("--output", default=os.getenv("MCP_REGISTRY_PATH", "mcp_endpoints.yml"))
    args = parser.parse_args()

    data = {"tools": discover(DEFAULT_SERVICES)}
    Path(args.output).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
