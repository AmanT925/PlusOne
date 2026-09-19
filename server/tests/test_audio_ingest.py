from importlib import reload

from fastapi.testclient import TestClient

from server.wavutil import pcm16_to_wav


def test_pcm16_to_wav_header():
    wav = pcm16_to_wav(b"\x00\x00" * 10, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_audio_endpoint_transcript_bypass(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_VOICE", "0")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")

    import server.main as main

    reload(main)

    wav = pcm16_to_wav(b"\x00\x00" * 160, sample_rate=16000)
    with TestClient(main.app) as client:
        response = client.post(
            "/rooms/demo/audio",
            data={
                "speaker": "sam",
                "visibility": "private:sam",
                "transcript": "I can't do more than $150",
            },
            files={"audio": ("u.wav", wav, "audio/wav")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["text"] == "I can't do more than $150"
        assert body["visibility"] == "private:sam"
        assert body["stt"] == "bypass"

        events = client.get("/rooms/demo/events").json()
        assert events[-1]["text"] == "I can't do more than $150"
