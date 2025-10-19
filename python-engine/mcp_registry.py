from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class MCPService:
    name: str
    endpoint: str
    display_name: str | None = None
    transport: str | None = None
    capabilities: List[str] | None = None
    health: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "MCPService":
        return cls(
            name=payload["name"],
            endpoint=payload["endpoint"],
            display_name=payload.get("displayName"),
            transport=payload.get("transport"),
            capabilities=payload.get("capabilities"),
            health=payload.get("health"),
        )


def load_registry(file_path: str | os.PathLike | None = None) -> List[MCPService]:
    """Load the MCP registry JSON file and return parsed services."""
    candidate = (
        Path(file_path) if file_path else Path(os.environ.get("MCP_ENDPOINTS_FILE", ""))
    )
    if not candidate:
        return []
    if not candidate.exists():
        return []
    with candidate.open("r", encoding="utf-8") as handle:
        raw: Iterable[dict] = json.load(handle)
    return [MCPService.from_dict(entry) for entry in raw]


__all__ = ["MCPService", "load_registry"]
