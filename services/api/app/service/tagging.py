"""Orchestration for the Tagging primary entity.

Reads audio bytes from B2, runs the local PANNs engine (repo/panns_engine.py),
writes a per-clip tag JSON to `tags/`, and rebuilds the `labels_index.jsonl`
manifest by listing `tags/` (idempotent — no read-modify-write race). Also backs
the sample-scoped Library and the corpus Dashboard.

All storage goes through the existing `repo/` B2 spine (boto3 stays confined
there); all inference goes through `repo/panns_engine.py` (torch/panns stay
confined there).
"""

import json
import logging
import math
from collections import Counter
from datetime import UTC, datetime

from pydantic import ValidationError

from app.config import settings
from app.repo import (
    delete_file,
    get_file_metadata,
    get_object_bytes,
    list_files,
    panns_engine,
    upload_file,
)
from app.service.files import FileKeyError, validate_key
from app.service.metadata import probe_audio
from app.types import (
    AudioMetadata,
    CorpusStats,
    Label,
    LibraryClip,
    ManifestEntry,
    Tagging,
    TaggingSummary,
    TopLabelCount,
)

logger = logging.getLogger(__name__)

AUDIO_PREFIX = "audio/"
TAGS_PREFIX = "tags/"
MANIFEST_KEY = "labels_index.jsonl"


class TaggingError(Exception):
    """Service-layer failure with an HTTP status the runtime maps directly."""

    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _tag_key_for(audio_key: str) -> str:
    return f"{TAGS_PREFIX}{audio_key}.json"


def _read_audio_bytes(audio_key: str) -> bytes:
    """Validate the key, confirm the clip exists and fits, and return its bytes."""
    try:
        validate_key(audio_key)
    except FileKeyError as e:
        raise TaggingError(e.detail, 400) from None
    metadata = get_file_metadata(audio_key)
    if not metadata:
        raise TaggingError(f"Audio clip not found: {audio_key}", 404)
    if metadata.size_bytes > settings.max_file_size:
        raise TaggingError("Clip too large to tag", 413)
    # RuntimeError (B2 failure) propagates and is mapped to 502 by the runtime.
    return get_object_bytes(audio_key)


def _tag_and_store(audio_key: str, model: str, top_k: int) -> Tagging:
    """Run PANNs over the clip, write the tag JSON, and rebuild the manifest."""
    audio_bytes = _read_audio_bytes(audio_key)
    source_meta = probe_audio(audio_bytes)

    try:
        result = panns_engine.tag_audio(
            audio_bytes, model_key=model, top_k=top_k
        )
    except panns_engine.ModelUnavailableError as e:
        raise TaggingError(str(e), 400) from None
    except Exception as e:
        logger.warning("PANNs tagging failed for %s", audio_key, exc_info=True)
        raise TaggingError(f"Failed to tag audio: {e}", 422) from None

    tag_key = _tag_key_for(audio_key)
    document = {
        "audio_key": audio_key,
        "model": result["model"],
        "top_k": result["top_k"],
        "labels": result["labels"],
        "embedding": result["embedding"],
        "embedding_dim": result["embedding_dim"],
        "tagged_at": datetime.now(UTC).isoformat(),
        "source_metadata": {
            "duration_seconds": source_meta.get("duration_seconds"),
            "sample_rate": source_meta.get("sample_rate"),
            "channels": source_meta.get("channels"),
        },
    }
    upload_file(
        json.dumps(document).encode("utf-8"), tag_key, "application/json"
    )
    _rebuild_manifest()
    return _tagging_from_document(document, tag_key)


def _tagging_from_document(document: dict, tag_key: str) -> Tagging:
    embedding = document.get("embedding", [])
    l2 = math.sqrt(sum(x * x for x in embedding)) if embedding else 0.0
    source = document.get("source_metadata") or {}
    return Tagging(
        audio_key=document["audio_key"],
        tag_key=tag_key,
        model=document["model"],
        top_k=document["top_k"],
        labels=[Label(**label) for label in document["labels"]],
        tagged_at=document["tagged_at"],
        duration_seconds=source.get("duration_seconds"),
        embedding=embedding,
        embedding_dim=document.get("embedding_dim", len(embedding)),
        embedding_l2_norm=l2,
        source_metadata=AudioMetadata(**source),
    )


def _read_tag_document(audio_key: str) -> dict:
    tag_key = _tag_key_for(audio_key)
    metadata = get_file_metadata(tag_key)
    if not metadata:
        raise TaggingError(f"No tagging for clip: {audio_key}", 404)
    try:
        return json.loads(get_object_bytes(tag_key))
    except json.JSONDecodeError:
        raise TaggingError("Stored tag JSON is corrupt", 502) from None


def _manifest_entry(document: dict, tag_key: str) -> ManifestEntry:
    source = document.get("source_metadata") or {}
    return ManifestEntry(
        audio_key=document["audio_key"],
        tag_key=tag_key,
        model=document["model"],
        top_k=document["top_k"],
        top_labels=[Label(**label) for label in document["labels"]],
        tagged_at=document["tagged_at"],
        duration_seconds=source.get("duration_seconds"),
    )


def _rebuild_manifest() -> None:
    """Rebuild labels_index.jsonl from scratch by listing every `tags/` object.

    Idempotent: the manifest is derived state, so we never read-modify-write it.
    A create/edit/run/delete just re-lists `tags/` and overwrites the manifest.
    """
    lines: list[str] = []
    for obj in list_files(prefix=TAGS_PREFIX):
        if not obj.key.endswith(".json"):
            continue
        try:
            document = json.loads(get_object_bytes(obj.key))
            entry = _manifest_entry(document, obj.key)
        except (json.JSONDecodeError, KeyError, ValidationError, RuntimeError):
            logger.warning("Skipping unreadable tag object: %s", obj.key)
            continue
        lines.append(entry.model_dump_json())
    body = ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
    upload_file(body, MANIFEST_KEY, "application/x-ndjson")


# --- Public service API ---------------------------------------------------


def create_tagging(audio_key: str, model: str, top_k: int) -> Tagging:
    return _tag_and_store(audio_key, model, top_k)


def edit_tagging(audio_key: str, model: str, top_k: int) -> Tagging:
    return _tag_and_store(audio_key, model, top_k)


def run_tagging(audio_key: str) -> Tagging:
    """Re-tag with the parameters stored in the existing tag JSON."""
    document = _read_tag_document(audio_key)
    return _tag_and_store(
        audio_key, document.get("model", panns_engine.DEFAULT_MODEL),
        document.get("top_k", 10),
    )


def get_tagging(audio_key: str) -> Tagging:
    document = _read_tag_document(audio_key)
    return _tagging_from_document(document, _tag_key_for(audio_key))


def delete_tagging(audio_key: str) -> None:
    tag_key = _tag_key_for(audio_key)
    metadata = get_file_metadata(tag_key)
    if not metadata:
        raise TaggingError(f"No tagging for clip: {audio_key}", 404)
    delete_file(tag_key)  # RuntimeError → 502 in the runtime
    _rebuild_manifest()


def get_manifest() -> list[ManifestEntry]:
    """Return the parsed labels_index.jsonl (empty if it doesn't exist yet)."""
    try:
        raw = get_object_bytes(MANIFEST_KEY)
    except RuntimeError:
        return []
    entries: list[ManifestEntry] = []
    for line in raw.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(ManifestEntry(**json.loads(line)))
        except (json.JSONDecodeError, ValidationError):
            continue
    return entries


def _summary_from_entry(entry: ManifestEntry) -> TaggingSummary:
    return TaggingSummary(
        audio_key=entry.audio_key,
        tag_key=entry.tag_key,
        model=entry.model,
        top_k=entry.top_k,
        labels=entry.top_labels,
        tagged_at=entry.tagged_at,
        duration_seconds=entry.duration_seconds,
    )


def list_taggings() -> list[TaggingSummary]:
    """List every Tagging (summary projection) via the cheap manifest read."""
    entries = get_manifest()
    entries.sort(key=lambda e: e.tagged_at, reverse=True)
    return [_summary_from_entry(e) for e in entries]


def get_library() -> list[LibraryClip]:
    """List sample-scoped clips under audio/ with tag status + known duration."""
    manifest = {e.audio_key: e for e in get_manifest()}
    clips: list[LibraryClip] = []
    for f in list_files(prefix=AUDIO_PREFIX):
        entry = manifest.get(f.key)
        clips.append(
            LibraryClip(
                key=f.key,
                filename=f.filename,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at,
                tagged=entry is not None,
                tag_key=entry.tag_key if entry else None,
                duration_seconds=entry.duration_seconds if entry else None,
            )
        )
    clips.sort(key=lambda c: c.uploaded_at, reverse=True)
    return clips


def get_corpus_stats() -> CorpusStats:
    """Aggregate dashboard metrics: coverage + top-label distribution."""
    clips_ingested = len(list_files(prefix=AUDIO_PREFIX))
    manifest = get_manifest()
    clips_tagged = len({e.audio_key for e in manifest})

    label_counts: Counter[str] = Counter()
    for entry in manifest:
        for label in entry.top_labels:
            label_counts[label.label] += 1

    recent = sorted(manifest, key=lambda e: e.tagged_at, reverse=True)[:5]
    return CorpusStats(
        clips_ingested=clips_ingested,
        clips_tagged=clips_tagged,
        pct_tagged=(
            round(100 * clips_tagged / clips_ingested, 1)
            if clips_ingested
            else 0.0
        ),
        distinct_labels=len(label_counts),
        top_labels=[
            TopLabelCount(label=label, count=count)
            for label, count in label_counts.most_common(10)
        ],
        recent_taggings=[_summary_from_entry(e) for e in recent],
    )
