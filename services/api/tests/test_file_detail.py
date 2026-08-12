"""Tests for on-demand rich-metadata recomputation (`GET /files-by-key/detail`).

The endpoint heads the object (existence + size guard), downloads its bytes,
and re-runs the real `extract_metadata()`. Here `get_file_metadata` and
`get_object_bytes` are stubbed at the service module; extraction runs for real
(audio metadata via soundfile, checksums for everything else).
"""

import hashlib
import io
import wave
from datetime import UTC, datetime

import pytest

from app.config import settings
from app.service import files as files_service
from app.types import FileMetadata

TEXT_BYTES = b"hello, world\n"
# A fixed *past* upload time, distinct from "now", so the timestamp assertion
# below proves the real upload time is threaded through the recompute.
UPLOADED_AT = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

WAV_SAMPLE_RATE = 16000
WAV_FRAMES = 8000  # 0.5s at 16 kHz


def _fake_metadata(
    key: str,
    *,
    content_type: str = "text/plain",
    size_bytes: int = len(TEXT_BYTES),
) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.rsplit("/", 1)[-1],
        folder="audio/",
        size_bytes=size_bytes,
        size_human=f"{size_bytes} B",
        content_type=content_type,
        uploaded_at=UPLOADED_AT,
        url=None,
    )


def _wav_bytes(sample_rate: int = WAV_SAMPLE_RATE, channels: int = 1,
               frames: int = WAV_FRAMES) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as writer:
        writer.setnchannels(channels)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"\x00\x00" * frames * channels)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_detail_returns_checksums_for_text_file(client, monkeypatch):
    monkeypatch.setattr(
        files_service, "get_file_metadata", lambda key: _fake_metadata(key)
    )
    monkeypatch.setattr(files_service, "get_object_bytes", lambda key: TEXT_BYTES)

    resp = await client.get(
        "/files-by-key/detail", params={"key": "audio/note.txt"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["md5"] == hashlib.md5(TEXT_BYTES).hexdigest()
    assert body["sha256"] == hashlib.sha256(TEXT_BYTES).hexdigest()
    assert body["extension"] == "txt"
    # The stored object's real upload time (head_object LastModified) is
    # threaded through the recompute — not the recompute wall-clock time.
    assert body["uploaded_at"].startswith("2026-01-02T03:04:05")
    # Non-audio: audio fields stay null and no warning is raised.
    assert body["duration_seconds"] is None
    assert body["sample_rate"] is None
    assert body["channels"] is None
    assert body["metadata_warning"] is None


@pytest.mark.asyncio
async def test_detail_extracts_audio_metadata(client, monkeypatch):
    wav = _wav_bytes()
    monkeypatch.setattr(
        files_service,
        "get_file_metadata",
        lambda key: _fake_metadata(
            key, content_type="audio/wav", size_bytes=len(wav)
        ),
    )
    monkeypatch.setattr(files_service, "get_object_bytes", lambda key: wav)

    resp = await client.get(
        "/files-by-key/detail", params={"key": "audio/clip.wav"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["sample_rate"] == WAV_SAMPLE_RATE
    assert body["channels"] == 1
    assert body["duration_seconds"] == pytest.approx(WAV_FRAMES / WAV_SAMPLE_RATE)
    assert body["metadata_warning"] is None


@pytest.mark.asyncio
async def test_detail_missing_file_returns_404(client, monkeypatch):
    monkeypatch.setattr(files_service, "get_file_metadata", lambda key: None)

    resp = await client.get(
        "/files-by-key/detail", params={"key": "audio/gone.wav"}
    )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_detail_oversized_file_rejected_without_download(client, monkeypatch):
    def _boom(key):  # pragma: no cover - must never run
        raise AssertionError("oversized object must not be downloaded")

    monkeypatch.setattr(
        files_service,
        "get_file_metadata",
        lambda key: _fake_metadata(
            key, size_bytes=settings.max_file_size + 1
        ),
    )
    monkeypatch.setattr(files_service, "get_object_bytes", _boom)

    resp = await client.get(
        "/files-by-key/detail", params={"key": "audio/huge.wav"}
    )

    assert resp.status_code == 413


def test_get_object_bytes_wraps_streaming_read_failure(monkeypatch):
    """A mid-stream read failure must become a RuntimeError, not escape.

    `get_object` can succeed while the body's `.read()` fails partway through a
    large download with a BotoCoreError (not a ClientError). The repo must wrap
    it so the runtime's RuntimeError->502 mapping holds instead of leaking a 500.
    """
    from botocore.exceptions import ResponseStreamingError

    from app.repo import b2_object

    class _Body:
        def read(self):
            raise ResponseStreamingError(error="connection reset mid-stream")

    class _Client:
        def get_object(self, **kwargs):
            return {"Body": _Body()}

    monkeypatch.setattr(b2_object, "get_s3_client", lambda: _Client())

    with pytest.raises(RuntimeError):
        b2_object.get_object_bytes("audio/big.wav")
