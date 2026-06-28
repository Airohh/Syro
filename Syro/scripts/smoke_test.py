"""Smoke test post-deploiement : verifie que tous les services repondent.

Usage (apres `docker-compose up -d`):
    python scripts/smoke_test.py
    python scripts/smoke_test.py --api-only   # sans Qdrant/Redis/MLflow

Stdlib uniquement (urllib + socket) : aucun prerequis pip.
Exit code 0 si tout est sain, 1 sinon.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request

DEFAULT_TIMEOUT = 5.0


def check_http(name: str, url: str, expect_json_key: str | None = None) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT) as resp:
            if resp.status >= 400:
                print(f"  FAIL  {name}: HTTP {resp.status} ({url})")
                return False
            if expect_json_key:
                body = json.loads(resp.read().decode("utf-8"))
                if expect_json_key not in body:
                    print(f"  FAIL  {name}: cle '{expect_json_key}' absente ({url})")
                    return False
            print(f"  OK    {name} ({url})")
            return True
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as e:
        print(f"  FAIL  {name}: {e} ({url})")
        return False


def check_tcp(name: str, host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=DEFAULT_TIMEOUT):
            print(f"  OK    {name} ({host}:{port})")
            return True
    except OSError as e:
        print(f"  FAIL  {name}: {e} ({host}:{port})")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Syro smoke test")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--mlflow-url", default="http://localhost:5000")
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--api-only", action="store_true", help="ne teste que l'API")
    args = parser.parse_args()

    print("Syro smoke test")
    print("=" * 50)

    results = [
        check_http("API /health", f"{args.api_url}/health", expect_json_key="status"),
        check_http("API /domains", f"{args.api_url}/domains"),
        check_http("API /docs (Swagger)", f"{args.api_url}/docs"),
    ]

    if not args.api_only:
        results += [
            check_http("Qdrant", f"{args.qdrant_url}/collections"),
            check_tcp("Redis", args.redis_host, args.redis_port),
            check_http("MLflow", args.mlflow_url),
        ]

    print("=" * 50)
    failed = results.count(False)
    if failed:
        print(f"{failed}/{len(results)} verification(s) en echec")
        return 1
    print(f"{len(results)}/{len(results)} OK — stack saine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
