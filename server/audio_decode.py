"""Normalize phone recordings to Muse's mono, 16-bit, 24 kHz WAV input."""

import io
import wave

from server.wavutil import pcm16_to_wav


def muse_wav(data: bytes, filename: str = "") -> bytes:
    if filename.lower().endswith((".pcm", ".raw")):
        if len(data) > 16000 * 2 * 90 or len(data) % 2:
            raise ValueError("Invalid or too-long PCM recording.")
        return pcm16_to_wav(data)
    try:
        with wave.open(io.BytesIO(data)) as wav:
            if (wav.getnchannels() == 1 and wav.getsampwidth() == 2
                    and wav.getframerate() in (16000, 24000)):
                if wav.getnframes() > wav.getframerate() * 90:
                    raise ValueError("Keep recordings under 90 seconds.")
                return pcm16_to_wav(wav.readframes(wav.getnframes()), sample_rate=wav.getframerate())
    except (wave.Error, EOFError):
        pass

    import av

    pcm = bytearray()
    try:
        with av.open(io.BytesIO(data)) as source:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=24000)
            for frame in source.decode(audio=0):
                for output in resampler.resample(frame):
                    pcm.extend(bytes(output.planes[0])[:output.samples * 2])
                if len(pcm) > 24000 * 2 * 90:
                    raise ValueError("Keep recordings under 90 seconds.")
            for output in resampler.resample(None):
                pcm.extend(bytes(output.planes[0])[:output.samples * 2])
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Could not decode recording. Try recording again.") from exc
    if not pcm:
        raise ValueError("Recording contains no audio.")
    return pcm16_to_wav(bytes(pcm), sample_rate=24000)
