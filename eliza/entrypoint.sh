#!/bin/bash
set -euo pipefail

if [[ -n "${MCP_ENDPOINTS:-}" ]]; then
  echo "[entrypoint] Generating MCP registry from ${MCP_ENDPOINTS}"
  node /app/scripts/register-tools.mjs "${MCP_ENDPOINTS}" "${MCP_REGISTRY_PATH:-/app/config/mcp-registry.json}"
else
  echo "[entrypoint] No MCP endpoints provided; skipping registry generation"
fi

exec bun run start
