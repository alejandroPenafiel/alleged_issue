# Modular MCP-Oriented Agent Platform

This repository provides an opinionated Docker Compose stack for orchestrating a Python data ingestion engine, ElizaOS, Redis, PostgreSQL, and multiple Model Context Protocol (MCP) servers. The goal is to simplify running a modular, agent-friendly environment where services can discover tool endpoints and share state through Redis.

## Overview

The stack launches the following containers:

| Service         | Role                                                                   |
| --------------- | ---------------------------------------------------------------------- |
| `python-engine` | Async WebSocket consumer that writes to Redis and emits Celery tasks.  |
| `eliza`         | ElizaOS AI runtime wired to Redis/PostgreSQL with automatic tool sync. |
| `redis`         | Cache, pub/sub hub, and Celery broker/result backend.                   |
| `postgres`      | Structured storage for ElizaOS and custom data.                        |
| `mcp-serena`    | Serena MCP server for AI-assisted code operations.                      |
| `mcp-redis`     | Redis MCP server exposing Redis data via natural language.              |
| `context7-mcp`  | Context7 MCP server for contextual project search.                      |

Shared volumes retain Redis/PostgreSQL persistence and cache MCP metadata so that developers benefit from warm tool state across restarts.

## Getting Started

1. Build the custom images and start the stack:

   ```bash
   docker compose up --build
   ```

2. Wait until all health checks pass. The Python engine and ElizaOS are held until Redis and PostgreSQL report healthy.

3. (Optional) Register MCP tools with ElizaOS:

   ```bash
   python scripts/register_mcp_tools.py --api-base http://localhost:3000
   ```

4. Inspect Redis notifications on channel `engine.results` or list Celery task metadata under the `engine:tasks` hash to observe ingestion activity.

## Tool Discovery

The `scripts/discover_mcp_endpoints.py` helper inspects running Docker containers (requires the Docker Engine API socket) and writes a registry file in JSON format that can be mounted by ElizaOS or the Python engine.

```bash
python scripts/discover_mcp_endpoints.py --output python-engine/config/mcp_endpoints.generated.yml
```

The default registry files bundled in `eliza/config` and `python-engine/config` are YAML documents that list the internal service endpoints for each MCP tool.

## Python Engine Implementation

The `python-engine/engine.py` module maintains a Redis connection, processes WebSocket events, and publishes results to Redis pub/sub while recording task metadata. When a message arrives it will:

1. Cache the latest payload at `engine:last_result`.
2. Publish the structured result to the `engine.results` channel.
3. Dispatch a Celery task (`python_engine.process_event`) for downstream asynchronous processing.
4. Queue MCP tool notifications so other agents can pick up pending work.

If the configured WebSocket feed is unavailable the engine falls back to a simulated stream for local testing.

## ElizaOS Integration

ElizaOS receives a mounted registry (`/app/config/mcp_endpoints.yml`) so the runtime can load MCP endpoints on boot. The included `scripts/register_mcp_tools.py` utility can also be executed in any Python environment to register those tools via ElizaOS's REST API (defaulting to `http://eliza:3000`).

## Extending the System

- Add new MCP servers by attaching services to the compose file and including them in the registry YAML.
- Provide a Celery worker service that reuses the `python-engine` image to handle background tasks if the ingestion work requires asynchronous processing.
- Mount additional project directories into the `context7-mcp` container to expand the searchable corpus for RAG workloads.

## Development Notes

- The compose file centralises health check defaults and shared environment values to keep service definitions concise.
- The Python engine image ships with async Redis/websocket dependencies and a simple health probe invoked from Docker.
- Context7 uses a writable workspace volume for caching indexes while binding in the host project read-only to avoid accidental mutations.
- The discovery helper depends on the `docker` Python package and access to the Docker
  Engine socket (e.g. `/var/run/docker.sock`).
