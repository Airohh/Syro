"""Charge le corpus de démo (evaluation/corpus) dans Syro via l'API HTTP.

Passe par le vrai chemin utilisateur : login → upload → ingestion par le
worker → documents interrogeables. Aucune dépendance (stdlib uniquement).

    make demo                                   # dans Docker
    python scripts/load_demo.py                 # depuis la machine hôte
    python scripts/load_demo.py --api http://localhost:8000 --email ... --password ...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "corpus"


def _request(url: str, *, data: bytes | None = None, headers: dict | None = None):
    """Requête JSON ; attend et réessaie si l'API limite le débit (HTTP 429)."""
    for _ in range(30):
        req = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(5)
    raise RuntimeError(f"Rate limit persistant sur {url}")


def login(api: str, email: str, password: str) -> str:
    body = urllib.parse.urlencode({"username": email, "password": password}).encode()
    return _request(
        f"{api}/auth/login",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )["access_token"]


def upload(api: str, token: str, path: Path, domain: str) -> int:
    boundary = uuid.uuid4().hex
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="domain"\r\n\r\n{domain}\r\n'.encode(),
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
            f'filename="{path.name}"\r\nContent-Type: text/markdown\r\n\r\n'
        ).encode()
        + path.read_bytes()
        + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    result = _request(
        f"{api}/documents/files",
        data=b"".join(parts),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    return result["document_id"]


def existing_filenames(api: str, token: str) -> set[str]:
    docs = _request(f"{api}/documents", headers={"Authorization": f"Bearer {token}"})
    return {
        d["filename"]
        for d in docs["documents"]
        if d["ingestion_status"] in ("complete", "queued", "processing")
    }


def wait(
    api: str, token: str, doc_ids: dict[int, str], timeout_s: int
) -> dict[int, dict]:
    headers = {"Authorization": f"Bearer {token}"}
    pending, done = dict(doc_ids), {}
    deadline = time.time() + timeout_s
    while pending and time.time() < deadline:
        for doc_id in list(pending):
            status = _request(f"{api}/documents/{doc_id}", headers=headers)
            if status["status"] in ("complete", "failed"):
                done[doc_id] = status
                name = pending.pop(doc_id)
                mark = "OK  " if status["status"] == "complete" else "FAIL"
                detail = (
                    f"{status['chunk_count']} chunks"
                    if status["status"] == "complete"
                    else status["error"]
                )
                print(f"  {mark} {name:<40} {detail}")
        if pending:
            time.sleep(1)
    for doc_id, name in pending.items():
        print(
            f"  ...  {name:<40} toujours en cours (voir docker compose logs syro-worker)"
        )
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description="Charge le corpus de démo dans Syro")
    parser.add_argument(
        "--api", default=os.environ.get("SYRO_API_URL", "http://localhost:8000")
    )
    parser.add_argument(
        "--email", default=os.environ.get("SYRO_ADMIN_EMAIL", "demo@syro.local")
    )
    parser.add_argument(
        "--password", default=os.environ.get("SYRO_ADMIN_PASSWORD", "syro-demo")
    )
    parser.add_argument("--timeout", type=int, default=600, help="attente max (s)")
    args = parser.parse_args()

    files = sorted(p for p in CORPUS_DIR.rglob("*.md") if p.parent != CORPUS_DIR)
    try:
        token = login(args.api, args.email, args.password)
    except (urllib.error.URLError, KeyError) as e:
        print(f"Connexion impossible à {args.api} ({e}). L'API est-elle démarrée ?")
        return 1

    already = existing_filenames(args.api, token)
    to_upload = [p for p in files if p.name not in already]
    print(
        f"{len(files)} documents de démo, {len(files) - len(to_upload)} déjà présents."
    )
    if not to_upload:
        return 0

    doc_ids = {}
    for path in to_upload:
        doc_ids[upload(args.api, token, path, domain=path.parent.name)] = path.name
    print(f"{len(doc_ids)} documents envoyés, ingestion en cours...\n")

    done = wait(args.api, token, doc_ids, args.timeout)
    ok = sum(1 for s in done.values() if s["status"] == "complete")
    print(f"\n{ok}/{len(doc_ids)} documents indexés.")
    return 0 if ok == len(doc_ids) else 1


if __name__ == "__main__":
    sys.exit(main())
