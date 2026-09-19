from fastapi.testclient import TestClient

from server.tests.fakes import FakeLinq


def test_http_utterance_and_events(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("LINQ_SKIP_VERIFY", "1")
    from server.main import app

    with TestClient(app) as client:
        response = client.post(
            "/rooms/demo/utterances",
            json={
                "speaker": "sam",
                "visibility": "private:sam",
                "text": "I can't do more than $150",
            },
        )
        assert response.status_code == 200
        events = client.get("/rooms/demo/events").json()
        assert events[0]["visibility"] == "private:sam"
        assert events[0]["speaker"] == "sam"


def test_linq_webhook_maps_dm_and_group(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("LINQ_SKIP_VERIFY", "1")
    monkeypatch.setenv("PLUSONE_HANDLES", "sam:+15551111111,priya:+15552222222")
    from importlib import reload
    import server.main as main

    reload(main)

    with TestClient(main.app) as client:
        fake = FakeLinq()
        main.app.state.hub.linq = fake
        main.app.state.handle_map = {"+15551111111": "sam", "+15552222222": "priya"}

        dm = client.post(
            "/linq/webhook",
            json={
                "event_type": "message.received",
                "event_id": "e-dm",
                "data": {
                    "chat": {"id": "chat-sam", "is_group": False},
                    "direction": "inbound",
                    "sender_handle": {"handle": "+15551111111"},
                    "parts": [{"type": "text", "value": "cap at $150"}],
                },
            },
        )
        assert dm.status_code == 200
        assert dm.json()["visibility"] == "private:sam"

        group = client.post(
            "/linq/webhook",
            json={
                "event_type": "message.received",
                "event_id": "e-g",
                "data": {
                    "chat": {"id": "chat-group", "is_group": True},
                    "direction": "inbound",
                    "sender_handle": {"handle": "+15552222222"},
                    "parts": [{"type": "text", "value": "fancy resort this weekend?"}],
                },
            },
        )
        assert group.status_code == 200
        assert group.json()["visibility"] == "public"

        events = client.get("/rooms/demo/events").json()
        vis = {e["text"]: e["visibility"] for e in events}
        assert vis["cap at $150"] == "private:sam"
        assert vis["fancy resort this weekend?"] == "public"

        sam_whispers = [m for m in fake.sent if m["chat_id"] == "chat-sam"]
        assert sam_whispers
        assert all(m["chat_id"] != "chat-group" for m in sam_whispers)

        dup = client.post(
            "/linq/webhook",
            json={
                "event_type": "message.received",
                "event_id": "e-dm",
                "data": {
                    "chat": {"id": "chat-sam", "is_group": False},
                    "direction": "inbound",
                    "sender_handle": {"handle": "+15551111111"},
                    "parts": [{"type": "text", "value": "cap at $150"}],
                },
            },
        )
        assert dup.json().get("duplicate") is True


def test_websocket_reconnect_replays_public(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("LINQ_SKIP_VERIFY", "1")
    from importlib import reload
    import server.main as main

    reload(main)

    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/demo/sam") as ws:
            joined = ws.receive_json()
            assert joined["type"] == "counter"
            ws.send_json(
                {"type": "utterance", "visibility": "public", "text": "hello table"}
            )
            public = ws.receive_json()
            assert public["type"] == "public"
            assert public["text"] == "hello table"

        with client.websocket_connect("/ws/demo/sam") as ws2:
            replayed = ws2.receive_json()
            assert replayed["type"] == "public"
            assert replayed["text"] == "hello table"


def test_health(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    from importlib import reload
    import server.main as main

    reload(main)
    with TestClient(main.app) as client:
        assert client.get("/health").json()["ok"] is True


def test_leaks_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_LLM", "0")
    from importlib import reload
    import server.main as main

    reload(main)
    with TestClient(main.app) as client:
        client.post(
            "/rooms/demo/utterances",
            json={"speaker": "sam", "visibility": "private:sam", "text": "I can't do more than $150"},
        )
        client.post(
            "/rooms/demo/utterances",
            json={"speaker": "priya", "visibility": "private:priya", "text": "I cannot be in a room with Alex"},
        )
        body = client.get("/rooms/demo/leaks").json()
        assert body["room"]["leaks"] == 0
        assert body["fixtures"]["leaks"] == 0
        assert body["fixtures"]["attempts"] >= 4
