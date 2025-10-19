from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict

DEFAULT_OUTPUT = Path(os.getenv("REGISTRY_OUTPUT", "/data/registry.json"))
DEFAULT_PORT = int(os.getenv("REGISTRY_PORT", "8500"))
DEFAULT_REFRESH = int(os.getenv("REGISTRY_REFRESH_SECONDS", "30"))


def parse_targets(raw: str) -> Dict[str, str]:
    targets: Dict[str, str] = {}
    for chunk in raw.split(","):
        if not chunk.strip():
            continue
        if "=" not in chunk:
            raise ValueError(f"Invalid target declaration: {chunk}")
        name, url = chunk.split("=", 1)
        targets[name.strip()] = url.strip()
    return targets


def write_registry(path: Path, targets: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_at": time.time(), "endpoints": targets}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def check_registry(path: Path) -> int:
    if not path.exists():
        print(f"Registry file {path} does not exist", flush=True)
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Registry file {path} is not valid JSON: {exc}", flush=True)
        return 2
    if "endpoints" not in data:
        print(f"Registry file {path} missing 'endpoints' key", flush=True)
        return 3
    return 0


def run_server(directory: Path, port: int) -> None:
    os.chdir(directory)
    server = ThreadingHTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Serving registry from {directory} on port {port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP registry helper")
    parser.add_argument("--serve", action="store_true", help="Run in HTTP server mode")
    parser.add_argument("--check", action="store_true", help="Validate registry file and exit")
    args = parser.parse_args()

    raw_targets = os.getenv("MCP_TARGETS", "").strip()
    targets = parse_targets(raw_targets) if raw_targets else {}
    write_registry(DEFAULT_OUTPUT, targets)

    if args.check:
        return check_registry(DEFAULT_OUTPUT)

    if args.serve:
        directory = DEFAULT_OUTPUT.parent
        thread = threading.Thread(target=run_server, args=(directory, DEFAULT_PORT), daemon=True)
        thread.start()
        try:
            while True:
                time.sleep(DEFAULT_REFRESH)
                if raw_targets:
                    write_registry(DEFAULT_OUTPUT, targets)
        except KeyboardInterrupt:
            pass
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
