# Agent Orchestration Stack

This repository provides a Docker-based reference architecture for an agentic platform that combines real-time ingestion, Redis-backed caching, ElizaOS reasoning, and Model Context Protocol (MCP) tooling.

## Overview

* **python-engine** – Async websocket consumer that streams data, writes to Redis, and emits Celery jobs.
* **ElizaOS** – RAG-capable agent host automatically configured with MCP tool metadata at startup.
* **Redis & PostgreSQL** – Shared cache, queue broker, and relational storage.
* **MCP Servers** – Serena, Redis MCP, and Context7 MCP for code search and datastore operations.

All services run on an isolated `agent-mesh` Docker network and expose only the ports that need to be reachable from the host.

## Getting Started

```bash
docker compose up --build
```

The compose project ensures Redis and PostgreSQL are healthy before starting dependent services. MCP servers become available to ElizaOS automatically thanks to the `register-tools.mjs` bootstrap script, which writes a registry file at `/app/config/mcp-registry.json` inside the Eliza container.

### Customising the Engine

Set `ENGINE_WEBSOCKET_URL` in your environment or `.env` file to point at the upstream websocket. The engine publishes validated events on the Redis pub/sub channel defined by `ENGINE_CHANNEL` and triggers the `python_engine.tasks.process_datapoint` Celery task for asynchronous processing.

### Discovering MCP Services Programmatically

Use `scripts/mcp_client.py` to probe the MCP servers from your workstation:

```bash
python scripts/mcp_client.py
```

It issues JSON-RPC calls against the `/mcp` endpoints to list capabilities so you can wire them into other agent frameworks.

### Shared Project Data

Mount project files into `./project-data` (host path) for Context7 to index. Each MCP server has a persistent volume for caches or metadata, making the system safe to restart without losing context.

## Extending the Mesh

New MCP services can be added by copying the `x-mcp-service` anchor in `docker-compose.yml`. As long as the container joins the `agent-mesh` network and advertises its endpoint in `MCP_ENDPOINTS`, ElizaOS will detect it automatically during startup.
