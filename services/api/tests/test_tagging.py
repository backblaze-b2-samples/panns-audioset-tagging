"""Tagging (primary-entity) API tests.

These exercise the full create / list / read / edit / delete / run lifecycle
against an in-memory fake of the B2 repo boundary, with the PANNs engine mocked
at the `app.service.tagging.panns_engine` module boundary. Nothing here imports
torch, panns-inference, or librosa — the engine is never actually loaded.
"""

import sys
from datetime import UTC, datetime

import pytest

from app.service import tagging as tagging_service
from app.types import FileMetadata

AUDIO_KEY = "audio/clip.wav"
TAG_KEY = "tags/audio/clip.wav.json"


class FakeB2:
    """A tiny in-memory object store standing in for the repo/B2 layer."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload_file(self, data: bytes, key: str, content_type: str) -> FileMetadata:
        self.objects[key] = data
        return self._meta(key)

    def get_object_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise RuntimeError(f"missing: {key}")
        return self.objects[key]

    def get_file_metadata(self, key: str) -> FileMetadata | None:
        if key not in self.objects:
            return None
        return self._meta(key)

    def list_files(self, prefix: str = "") -> list[FileMetadata]:
        return [self._meta(k) for k in self.objects if k.startswith(prefix)]

    def delete_file(self, key: str) -> None:
        self.objects.pop(key, None)

    def _meta(self, key: str) -> FileMetadata:
        data = self.objects.get(key, b"")
        folder, _, filename = key.rpartition("/")
        return FileMetadata(
            key=key,
            filename=filename or key,
            folder=f"{folder}/" if folder else "",
            size_bytes=len(data),
            size_human=f"{len(data)} B",
            content_type="audio/wav",
            uploaded_at=datetime.now(UTC),
            url=None,
        )


def _fake_tag_audio(audio_bytes, *, model_key, top_k):
    return {
        "labels": [
            {"label": f"Label{i}", "probability": round(0.95 - i * 0.05, 4)}
            for i in range(top_k)
        ],
        "embedding": [0.1] * 2048,
        "embedding_dim": 2048,
        "model": model_key,
        "top_k": top_k,
        "sample_rate": 32000,
    }


@pytest.fixture
def store(monkeypatch):
    """Wire an in-memory B2 + a mocked PANNs engine into the tagging service."""
    fake = FakeB2()
    # Seed one ingested clip under audio/.
    fake.objects[AUDIO_KEY] = b"RIFFfake-wav-bytes"

    for name in ("upload_file", "get_object_bytes", "get_file_metadata",
                 "list_files", "delete_file"):
        monkeypatch.setattr(tagging_service, name, getattr(fake, name))
    monkeypatch.setattr(
        tagging_service, "probe_audio",
        lambda data: {"duration_seconds": 1.5, "sample_rate": 32000, "channels": 1},
    )
    monkeypatch.setattr(
        tagging_service.panns_engine, "tag_audio", _fake_tag_audio
    )
    return fake


@pytest.mark.asyncio
async def test_create_read_list_and_library(client, store):
    resp = await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["audio_key"] == AUDIO_KEY
    assert body["tag_key"] == TAG_KEY
    assert len(body["labels"]) == 5
    assert body["embedding_dim"] == 2048
    assert len(body["embedding"]) == 2048
    assert body["embedding_l2_norm"] > 0
    assert body["source_metadata"]["sample_rate"] == 32000

    # The tag JSON and the manifest were both written to the store.
    assert TAG_KEY in store.objects
    assert "labels_index.jsonl" in store.objects

    listed = (await client.get("/taggings")).json()
    assert len(listed) == 1
    assert listed[0]["audio_key"] == AUDIO_KEY

    detail = (
        await client.get("/taggings/detail", params={"audio_key": AUDIO_KEY})
    ).json()
    assert len(detail["embedding"]) == 2048

    library = (await client.get("/library")).json()
    clip = next(c for c in library if c["key"] == AUDIO_KEY)
    assert clip["tagged"] is True
    assert clip["duration_seconds"] == 1.5


@pytest.mark.asyncio
async def test_create_missing_clip_returns_404(client, store):
    resp = await client.post(
        "/taggings",
        json={"audio_key": "audio/nope.wav", "model": "cnn14-32k", "top_k": 5},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_top_k_rejected(client, store):
    resp = await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 7},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_edit_changes_params(client, store):
    await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    resp = await client.post(
        "/taggings/edit",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-16k", "top_k": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model"] == "cnn14-16k"
    assert len(body["labels"]) == 10


@pytest.mark.asyncio
async def test_run_recomputes_with_stored_params(client, store):
    await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    resp = await client.post("/taggings/run", json={"audio_key": AUDIO_KEY})
    assert resp.status_code == 200
    # Stored params were top_k=5, so the re-tag keeps 5 labels.
    assert len(resp.json()["labels"]) == 5


@pytest.mark.asyncio
async def test_run_without_existing_tagging_404(client, store):
    resp = await client.post("/taggings/run", json={"audio_key": AUDIO_KEY})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_tagging_and_manifest_line(client, store):
    await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    resp = await client.delete("/taggings", params={"audio_key": AUDIO_KEY})
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert TAG_KEY not in store.objects
    assert (await client.get("/taggings")).json() == []


@pytest.mark.asyncio
async def test_manifest_and_corpus_stats(client, store):
    await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    manifest = (await client.get("/taggings/manifest")).json()
    assert len(manifest) == 1
    assert manifest[0]["audio_key"] == AUDIO_KEY
    assert len(manifest[0]["top_labels"]) == 5

    stats = (await client.get("/taggings/stats")).json()
    assert stats["clips_ingested"] == 1
    assert stats["clips_tagged"] == 1
    assert stats["pct_tagged"] == 100.0
    assert stats["distinct_labels"] == 5


@pytest.mark.asyncio
async def test_engine_stays_unloaded(client, store):
    """The mocked engine path must never pull torch/panns into the process."""
    await client.post(
        "/taggings",
        json={"audio_key": AUDIO_KEY, "model": "cnn14-32k", "top_k": 5},
    )
    assert "torch" not in sys.modules
    assert "panns_inference" not in sys.modules
