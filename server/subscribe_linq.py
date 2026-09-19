"""Create or update a Linq webhook subscription for this machine's HTTPS tunnel.

Never prints signing secrets. Use --write-env to store LINQ_WEBHOOK_SECRET in .env.

    python -m server.subscribe_linq https://abc123.ngrok-free.app --write-env
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

from server.envload import linq_api_key, load_plusone_env
from server.linq import LINQ_API

ROOT = Path(__file__).resolve().parents[1]


def _headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _write_env_secret(secret: str) -> None:
    env_path = ROOT / ".env"
    text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = [ln for ln in text.splitlines() if not ln.startswith("LINQ_WEBHOOK_SECRET=")]
    lines.append(f"LINQ_WEBHOOK_SECRET={secret}")
    if not any(ln.startswith("LINQ_FROM=") for ln in lines):
        lines.append("LINQ_FROM=+19492783794")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def subscribe(origin: str, *, write_env: bool = True) -> int:
    load_plusone_env()
    key = linq_api_key()
    if not key:
        print("No LINQ / LINQ_API_KEY in .env", file=sys.stderr)
        return 1

    origin = origin.strip().rstrip("/")
    if not origin.startswith("https://"):
        print("Tunnel URL must be https://...", file=sys.stderr)
        return 1
    target = f"{origin}/linq/webhook?version=2026-02-03"
    headers = _headers(key)
    body = {"target_url": target, "subscribed_events": ["message.received"]}

    listed = httpx.get(f"{LINQ_API}/webhook-subscriptions", headers=headers, timeout=30.0)
    existing_id = None
    if listed.status_code < 400:
        payload = listed.json()
        subs = payload.get("subscriptions") or payload.get("data") or []
        if isinstance(payload, list):
            subs = payload
        if subs:
            existing_id = subs[0].get("id")

    if existing_id:
        if os.environ.get("LINQ_WEBHOOK_SECRET"):
            print("Updating existing Linq webhook to this tunnel…")
            response = httpx.put(
                f"{LINQ_API}/webhook-subscriptions/{existing_id}",
                headers=headers,
                content=json.dumps(body),
                timeout=30.0,
            )
            if response.status_code >= 400:
                print(f"Update failed HTTP {response.status_code}", file=sys.stderr)
                return 1
            print("Webhook pointed at this tunnel. Using LINQ_WEBHOOK_SECRET already in .env.")
            return 0
        print("Old Linq subscription has no saved secret. Deleting it so Linq will issue a new one…")
        deleted = httpx.delete(
            f"{LINQ_API}/webhook-subscriptions/{existing_id}",
            headers=headers,
            timeout=30.0,
        )
        if deleted.status_code >= 400:
            print(f"Delete failed HTTP {deleted.status_code}", file=sys.stderr)
            return 1


    print("Creating Linq webhook subscription…")
    response = httpx.post(
        f"{LINQ_API}/webhook-subscriptions",
        headers=headers,
        content=json.dumps(body),
        timeout=30.0,
    )
    if response.status_code >= 400:
        print(f"Create failed HTTP {response.status_code}", file=sys.stderr)
        return 1
    secret = response.json().get("signing_secret")
    if not secret:
        print("Linq did not return a signing secret.", file=sys.stderr)
        return 1
    if write_env:
        _write_env_secret(secret)
        os.environ["LINQ_WEBHOOK_SECRET"] = secret
        print("Saved webhook secret to .env (not shown).")
    else:
        print("Created subscription. Re-run with --write-env to save the secret.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tunnel", help="ngrok https origin, no path")
    parser.add_argument("--write-env", action="store_true")
    args = parser.parse_args()
    return subscribe(args.tunnel, write_env=args.write_env)


if __name__ == "__main__":
    raise SystemExit(main())
