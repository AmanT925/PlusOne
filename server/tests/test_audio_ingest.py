from importlib import reload

from fastapi.testclient import TestClient

from server.wavutil import pcm16_to_wav
from server.xai_media import still_prompt


def test_pcm16_to_wav_header():
    wav = pcm16_to_wav(b"\x00\x00" * 10, sample_rate=16000)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def phone_recording():
    """Real AAC in an MP4 container, matching Expo's native recording preset."""
    import io
    import av

    target = io.BytesIO()
    with av.open(target, mode="w", format="mp4") as output:
        stream = output.add_stream("aac", rate=44100)
        stream.layout = "mono"
        frame = av.AudioFrame(format="fltp", layout="mono", samples=44100)
        frame.sample_rate = 44100
        frame.planes[0].update(bytes(frame.planes[0].buffer_size))
        for packet in stream.encode(frame):
            output.mux(packet)
        for packet in stream.encode(None):
            output.mux(packet)
    return target.getvalue()


def test_phone_audio_transcribed_and_routed_privately(tmp_path, monkeypatch):
    import io
    import wave
    import server.main as main

    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "voice.db"))
    reload(main)
    monkeypatch.setattr("server.stt.stt_enabled", lambda: True)

    async def transcribe(wav_bytes):
        with wave.open(io.BytesIO(wav_bytes)) as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 24000
            assert 23000 < wav.getnframes() < 26000
        return "I cannot spend more than $150"

    monkeypatch.setattr("server.stt.transcribe_wav", transcribe)
    with TestClient(main.app) as client:
        response = client.post(
            "/rooms/voice/audio",
            data={"speaker": "sam", "visibility": "private:someone-else"},
            files={"audio": ("recording.m4a", phone_recording(), "audio/mp4")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["stt"] == "muse"
        assert response.json()["visibility"] == "private:sam"
        events = client.get("/rooms/voice/events").json()
        assert events[0]["text"] == "I cannot spend more than $150"
        assert events[0]["visibility"] == "private:sam"


def test_invalid_recording_never_reaches_muse(tmp_path, monkeypatch):
    import server.main as main

    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "invalid.db"))
    reload(main)
    monkeypatch.setattr("server.stt.stt_enabled", lambda: True)

    async def unexpected(_):
        raise AssertionError("Invalid input must not be sent to Muse")

    monkeypatch.setattr("server.stt.transcribe_wav", unexpected)
    with TestClient(main.app) as client:
        response = client.post(
            "/rooms/voice/audio", data={"speaker": "sam"},
            files={"audio": ("recording.m4a", b"not audio", "audio/mp4")},
        )
        assert response.status_code == 400
        assert client.get("/rooms/voice/events").json() == []


def test_audio_endpoint_transcript_bypass(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_LLM", "0")
    monkeypatch.setenv("PLUSONE_TTS", "0")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")
    monkeypatch.setenv("PLUSONE_STT", "0")

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
        assert events[-1]["visibility"] == "private:sam"


def test_audio_endpoint_stt_off_without_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_STT", "0")
    monkeypatch.delenv("MUSE_API_KEY", raising=False)
    monkeypatch.delenv("MUSE_TRANSCRIBE_KEY", raising=False)
    monkeypatch.delenv("MODEL_API_KEY", raising=False)

    import server.main as main

    reload(main)

    wav = pcm16_to_wav(b"\x00\x00" * 160, sample_rate=16000)
    with TestClient(main.app) as client:
        response = client.post(
            "/rooms/demo/audio",
            data={"speaker": "sam", "visibility": "private:sam"},
            files={"audio": ("u.wav", wav, "audio/wav")},
        )
        assert response.status_code == 503


def test_whisper_mp3_after_private_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_LLM", "0")
    monkeypatch.setenv("PLUSONE_TTS", "1")
    monkeypatch.setenv("PLUSONE_IMAGINE", "0")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    fake_mp3 = b"ID3" + b"\x00" * 80

    async def fake_speak(text: str):
        assert text
        return fake_mp3

    import server.main as main

    reload(main)
    monkeypatch.setattr("server.xai_media.speak_whisper", fake_speak)

    with TestClient(main.app) as client:
        posted = client.post(
            "/rooms/demo/utterances",
            json={
                "speaker": "nirvan",
                "visibility": "private:nirvan",
                "text": "I can't do more than $150",
            },
        )
        assert posted.status_code == 200, posted.text
        audio = client.get("/rooms/demo/users/nirvan/whisper.mp3")
        assert audio.status_code == 200
        assert audio.headers["content-type"].startswith("audio/mpeg")
        assert audio.content == fake_mp3


def test_imagine_prompt_uses_public_suggestion(tmp_path, monkeypatch):
    monkeypatch.setenv("PLUSONE_DB", str(tmp_path / "plusone.db"))
    monkeypatch.setenv("PLUSONE_LLM", "0")
    monkeypatch.setenv("PLUSONE_TTS", "0")
    monkeypatch.setenv("PLUSONE_IMAGINE", "1")
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    captured: list[str] = []

    async def fake_imagine(prompt: str):
        captured.append(prompt)
        return "https://example.test/still.png"

    import server.main as main

    reload(main)
    monkeypatch.setattr("server.xai_media.imagine_still", fake_imagine)

    with TestClient(main.app) as client:
        client.post(
            "/rooms/demo/utterances",
            json={
                "speaker": "sam",
                "visibility": "private:sam",
                "text": "I can't do more than $150",
            },
        )
        table = client.post(
            "/rooms/demo/utterances",
            json={
                "speaker": "maya",
                "visibility": "public",
                "text": "let's go to Switzerland this weekend at a fancy resort",
            },
        )
        assert table.status_code == 200, table.text
        events = client.get("/rooms/demo/events").json()
        suggestion = next(
            e["text"] for e in events if e["speaker"] == "plus-one" and e["visibility"] == "public"
        )
        media = client.get("/rooms/demo/media").json()
        assert media["imagine_url"] == "https://example.test/still.png"
        assert captured, "imagine_still should run with the public suggestion"
        assert suggestion[:120] in captured[0]
        assert "picnic" not in captured[0].lower() or "picnic" in suggestion.lower()
        assert "sam" not in captured[0].lower()
        assert "private:" not in captured[0].lower()


def test_still_prompt_never_hardcodes_picnic():
    prompt = still_prompt("a mid-range dinner downtown instead of the Alps")
    assert "picnic" not in prompt.lower()
    assert "mid-range dinner downtown" in prompt
    assert "sam" not in still_prompt("Sam cannot spend more than $150").lower()
