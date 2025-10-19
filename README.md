# Multi-Agent MCP Orchestration Stack

This project wires together a Python data ingestion engine, ElizaOS, Redis, PostgreSQL, and a suite of Model Context Protocol (MCP) servers. Docker Compose orchestrates the services and coordinates their health, startup order, and shared metadata.

## Highlights

- **Python Engine** – Consumes a websocket stream, normalizes the data, caches it in Redis, emits pub/sub messages, and optionally schedules Celery work.
- **ElizaOS** – Built from source with Bun, configured to auto-register MCP tools via a shared registry file.
- **Redis & PostgreSQL** – Provide caching, queueing, and structured persistence with durable named volumes.
- **MCP Servers** – Serena, mcp-redis, and Context7 ship with persistent caches and consistent registration metadata.
- **Tool Registrar** – Lightweight Python job that bootstraps Eliza with the available MCP endpoints.

See [`docker-compose.yml`](docker-compose.yml) for complete service definitions.
