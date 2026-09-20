"""Minimal PCM16 mono WAV writer (no scipy)."""

from __future__ import annotations

import struct


def pcm16_to_wav(pcm: bytes, *, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wrap raw little-endian PCM16 as a RIFF/WAVE blob for Muse STT."""
    if channels < 1:
        raise ValueError("channels must be >= 1")
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2
    data_size = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        16,
        b"data",
        data_size,
    )
    return header + pcm
