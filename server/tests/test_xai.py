import httpx
import pytest

from server import xai


@pytest.mark.asyncio
async def test_synthesize_speech_returns_bytes(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/tts"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, content=b"ID3fake-mp3")

    transport = httpx.MockTransport(handler)

    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    audio = await xai.synthesize_speech("hello whisper")
    assert audio.startswith(b"ID3")


@pytest.mark.asyncio
async def test_generate_image_returns_url(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/images/generations"
        return httpx.Response(
            200,
            json={"data": [{"url": "https://cdn.x.ai/trip.png"}]},
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    result = await xai.generate_image("friends on a weekend trip")
    assert result["url"] == "https://cdn.x.ai/trip.png"


def test_trip_still_prompt_includes_proposal():
    prompt = xai.trip_still_prompt("cabin under $150")
    assert "cabin under $150" in prompt
