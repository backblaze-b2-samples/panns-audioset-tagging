"""A skipped/failed audio extractor must be reported, not silently omitted.

An audio clip whose header can't be read used to (in the image/PDF starter)
return a detail payload with no media section and no explanation. The safety
stance is kept: the skip is surfaced in `metadata_warning` while checksums and
size stay exact.
"""

import io
import wave

import pytest

from app.service.metadata import extract_metadata

WAV_SAMPLE_RATE = 16000
WAV_FRAMES = 8000


def _wav_bytes(sample_rate: int = WAV_SAMPLE_RATE, channels: int = 1,
               frames: int = WAV_FRAMES) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x00\x00" * frames * channels)
    return buf.getvalue()


def test_decodable_audio_has_metadata_and_no_warning():
    detail = extract_metadata(_wav_bytes(), "clip.wav", "audio/wav")
    assert detail.sample_rate == WAV_SAMPLE_RATE
    assert detail.channels == 1
    assert detail.duration_seconds == pytest.approx(WAV_FRAMES / WAV_SAMPLE_RATE)
    assert detail.metadata_warning is None


def test_undecodable_audio_is_reported():
    detail = extract_metadata(b"not audio at all", "broken.wav", "audio/wav")
    assert detail.sample_rate is None
    assert detail.duration_seconds is None
    assert detail.metadata_warning is not None
    assert detail.metadata_warning.startswith("Audio metadata unavailable")
    # Core fields still exact — the warning must not imply the file is broken.
    assert detail.md5
    assert detail.sha256
    assert detail.size_bytes == len(b"not audio at all")


def test_non_audio_types_carry_no_warning():
    detail = extract_metadata(b"col_a,col_b\n1,2\n", "data.csv", "text/csv")
    assert detail.metadata_warning is None
    assert detail.duration_seconds is None


@pytest.mark.asyncio
async def test_detail_route_exposes_the_warning(client, monkeypatch):
    """The field has to survive the response model, not just the service."""
    from datetime import UTC, datetime

    from app.service import files as files_service
    from app.types import FileMetadata

    payload = b"this is not a valid audio container"

    monkeypatch.setattr(
        files_service,
        "get_file_metadata",
        lambda key: FileMetadata(
            key=key,
            filename="broken.wav",
            folder="audio/",
            size_bytes=len(payload),
            size_human="1.0 KB",
            content_type="audio/wav",
            uploaded_at=datetime.now(UTC),
            url=None,
        ),
    )
    monkeypatch.setattr(files_service, "get_object_bytes", lambda key: payload)

    response = await client.get(
        "/files-by-key/detail", params={"key": "audio/broken.wav"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["duration_seconds"] is None
    assert body["metadata_warning"].startswith("Audio metadata unavailable")
