"""Linq iMessage/RCS/SMS adapter: webhook verify, inbound mapping, outbound send.

Mapping (contracts/README.md):
  one-on-one inbound -> Event visibility private:<user>
  group inbound      -> Event visibility public
  whisper            -> send to that person's one-on-one thread
  public suggestion  -> send to the group thread
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

from server.envload import linq_api_key

log = logging.getLogger("plusone.linq")

LINQ_API = "https://api.linqapp.com/api/partner/v3"


@dataclass(frozen=True)
class InboundMessage:
    event_id: str
    chat_id: str
    is_group: bool
    speaker_handle: str
    text: str
    direction: str


def parse_handle_map(raw: str | None = None) -> dict[str, str]:
    """PLUSONE_HANDLES=sam:+15551111111,priya:+15552222222 -> phone -> user."""
    raw = raw if raw is not None else os.environ.get("PLUSONE_HANDLES", "")
    mapping: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        user, phone = part.split(":", 1)
        user, phone = user.strip(), phone.strip()
        if user and phone:
            mapping[phone] = user
    return mapping


def user_from_handle(handle: str, handle_map: dict[str, str]) -> str:
    return handle_map.get(handle, handle)


def extract_text(parts: Any) -> str:
    if not isinstance(parts, list):
        return ""
    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and part.get("value"):
            chunks.append(str(part["value"]))
    return "\n".join(chunks).strip()


def parse_inbound(payload: dict[str, Any]) -> InboundMessage | None:
    """Accept both webhook versions 2026-02-03 (v2) and 2025-01-01 (v1)."""
    event_type = payload.get("event_type") or payload.get("type")
    if event_type and event_type not in ("message.received",):
        return None

    event_id = str(payload.get("event_id") or payload.get("id") or "")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return None

    # Ignore our own outbound echoes so we don't log whispers as user events.
    direction = str(data.get("direction") or "").lower()
    if direction == "outbound" or data.get("is_from_me") is True:
        return None

    chat = data.get("chat") if isinstance(data.get("chat"), dict) else {}
    chat_id = str(chat.get("id") or data.get("chat_id") or "")
    if not chat_id:
        return None
    is_group = bool(chat.get("is_group") if "is_group" in chat else data.get("is_group"))

    sender = data.get("sender_handle")
    if isinstance(sender, dict):
        speaker = str(sender.get("handle") or "")
    else:
        speaker = str(data.get("from") or data.get("sender") or "")
    if not speaker:
        return None

    message = data.get("message") if isinstance(data.get("message"), dict) else None
    parts = data.get("parts") if "parts" in data else (message.get("parts") if message else None)
    text = extract_text(parts)
    if not text:
        return None

    if not event_id:
        event_id = str(data.get("id") or f"{chat_id}:{speaker}:{text[:40]}")

    return InboundMessage(
        event_id=event_id,
        chat_id=chat_id,
        is_group=is_group,
        speaker_handle=speaker,
        text=text,
        direction=direction or "inbound",
    )


def visibility_for(inbound: InboundMessage, user: str) -> str:
    if inbound.is_group:
        return "public"
    return f"private:{user}"


def verify_signature(
    secret: str,
    body: bytes | str,
    headers: dict[str, str],
    *,
    now: float | None = None,
    max_age: int = 300,
) -> bool:
    """Standard Webhooks verification (Linq docs)."""
    if isinstance(body, bytes):
        body_str = body.decode("utf-8")
    else:
        body_str = body

    lower = {k.lower(): v for k, v in headers.items()}
    msg_id = lower.get("webhook-id")
    timestamp = lower.get("webhook-timestamp")
    signature = lower.get("webhook-signature")
    if not (msg_id and timestamp and signature):
        return False

    try:
        ts = int(timestamp)
    except ValueError:
        return False
    current = time.time() if now is None else now
    if abs(current - ts) > max_age:
        return False

    secret_str = secret.removeprefix("whsec_")
    try:
        key = base64.b64decode(secret_str)
    except Exception:
        return False

    signed_content = f"{msg_id}.{timestamp}.{body_str}"
    expected = base64.b64encode(
        hmac.new(key, signed_content.encode("utf-8"), hashlib.sha256).digest()
    ).decode()

    for sig in signature.split(" "):
        if sig.startswith("v1,") and hmac.compare_digest(expected, sig[3:]):
            return True
    return False


class LinqClient:
    def __init__(self, api_key: str | None = None, timeout: float = 15.0) -> None:
        self.api_key = api_key if api_key is not None else linq_api_key()
        self._http = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def start_typing(self, chat_id: str) -> None:
        if not self.enabled() or not chat_id:
            return
        url = f"{LINQ_API}/chats/{chat_id}/typing"
        try:
            response = await self._http.post(url, headers=self._headers())
            if response.status_code >= 400:
                log.warning("linq typing failed %s %s", response.status_code, response.text)
        except httpx.HTTPError:
            log.exception("linq typing request failed")

    async def send_text(self, text: str, *, chat_id: str | None = None, to: str | None = None) -> None:
        if not self.enabled():
            log.info("linq send skipped (no LINQ_API_KEY): %s", text[:80])
            return
        body = {"message": {"parts": [{"type": "text", "value": text}]}}
        from_number = os.environ.get("LINQ_FROM", "").strip()
        if chat_id:
            url = f"{LINQ_API}/chats/{chat_id}/messages"
        elif to:
            url = f"{LINQ_API}/messages"
            body["to"] = [to]
            if from_number:
                body["from"] = from_number
        else:
            log.warning("linq send skipped: no chat_id or to")
            return
        try:
            response = await self._http.post(url, headers=self._headers(), content=json.dumps(body))
            if response.status_code >= 400:
                log.warning("linq send failed %s %s", response.status_code, response.text)
        except httpx.HTTPError:
            log.exception("linq send request failed")
