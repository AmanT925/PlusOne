from importlib import reload

from fastapi.testclient import TestClient

from server.tests.fakes import FakeLinq


def test_whisper_sends_linq_voice_memo_when_tts_works(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("LINQ_SKIP_VERIFY", "1")
    monkeypatch.setenv("PLUSONE_VOICE", "1")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    import server.main as main
    import server.xai as xai

    reload(main)

    async def fake_tts(text: str, **kwargs):
        return b"ID3fake-whisper-audio"

    monkeypatch.setattr(xai, "synthesize_speech", fake_tts)

    with TestClient(main.app) as client:
        fake = FakeLinq()
        main.app.state.hub.linq = fake
        main.app.state.store.bind_chat("chat-sam", "demo", "dm", "sam")

        response = client.post(
            "/rooms/demo/utterances",
            json={
                "speaker": "sam",
                "visibility": "private:sam",
                "text": "I can't do more than $150",
            },
        )
        assert response.status_code == 200
        assert fake.sent, "text whisper still required"
        assert fake.voice_memos, "Grok Voice should become a Linq voice memo"
        assert fake.voice_memos[0]["chat_id"] == "chat-sam"
        assert fake.uploads and fake.uploads[0]["content_type"] == "audio/mpeg"


def test_demo_voice_endpoint_serves_media(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_VOICE", "1")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    import server.main as main
    import server.xai as xai

    reload(main)

    async def fake_tts(text: str, **kwargs):
        return b"ID3demo"

    monkeypatch.setattr(xai, "synthesize_speech", fake_tts)

    with TestClient(main.app) as client:
        created = client.post("/demo/sponsors/voice", json={"text": "hello"})
        assert created.status_code == 200
        path = created.json()["media_path"]
        audio = client.get(path)
        assert audio.status_code == 200
        assert audio.content == b"ID3demo"
