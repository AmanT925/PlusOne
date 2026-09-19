import base64
import hashlib
import hmac
import time

from server.linq import parse_handle_map, parse_inbound, user_from_handle, verify_signature, visibility_for


def test_parse_handle_map():
    mapping = parse_handle_map("sam:+15551111111, priya:+15552222222")
    assert mapping["+15551111111"] == "sam"
    assert user_from_handle("+15551111111", mapping) == "sam"
    assert user_from_handle("+1999", mapping) == "+1999"


def test_parse_inbound_v2_dm():
    payload = {
        "event_type": "message.received",
        "event_id": "evt-1",
        "data": {
            "chat": {"id": "chat-dm", "is_group": False},
            "direction": "inbound",
            "sender_handle": {"handle": "+15551111111"},
            "parts": [{"type": "text", "value": "budget $150"}],
        },
    }
    inbound = parse_inbound(payload)
    assert inbound is not None
    assert inbound.chat_id == "chat-dm"
    assert inbound.is_group is False
    assert inbound.text == "budget $150"
    assert visibility_for(inbound, "sam") == "private:sam"


def test_parse_inbound_v2_group():
    payload = {
        "event_type": "message.received",
        "event_id": "evt-2",
        "data": {
            "chat": {"id": "chat-g", "is_group": True},
            "direction": "inbound",
            "sender_handle": {"handle": "+15552222222"},
            "parts": [{"type": "text", "value": "fancy resort?"}],
        },
    }
    inbound = parse_inbound(payload)
    assert inbound is not None
    assert inbound.is_group is True
    assert visibility_for(inbound, "priya") == "public"


def test_ignores_outbound():
    payload = {
        "event_type": "message.received",
        "event_id": "evt-3",
        "data": {
            "chat": {"id": "chat-dm", "is_group": False},
            "direction": "outbound",
            "sender_handle": {"handle": "+15550000"},
            "parts": [{"type": "text", "value": "whisper"}],
        },
    }
    assert parse_inbound(payload) is None


def test_ignores_non_received_events():
    assert parse_inbound({"event_type": "message.delivered", "data": {}}) is None


def test_verify_signature_roundtrip():
    secret = "whsec_" + base64.b64encode(b"supersecretkeybytes!!").decode()
    body = b'{"event_type":"message.received"}'
    ts = str(int(time.time()))
    msg_id = "msg_abc"
    key = base64.b64decode(secret.removeprefix("whsec_"))
    expected = base64.b64encode(
        hmac.new(key, f"{msg_id}.{ts}.{body.decode()}".encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": ts,
        "webhook-signature": f"v1,{expected}",
    }
    assert verify_signature(secret, body, headers) is True
    headers["webhook-signature"] = "v1,aaaa"
    assert verify_signature(secret, body, headers) is False
