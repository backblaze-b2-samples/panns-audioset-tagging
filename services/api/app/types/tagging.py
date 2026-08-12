"""Pydantic models for the Tagging primary entity and the audio Library.

A `Tagging` is the result of running PANNs over one audio clip, persisted as
`tags/<audio_key>.json` in B2. The list/detail split keeps the heavy 2048-dim
embedding out of list responses.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Finite, selector-backed fields (mirrored by the frontend create/edit forms).
ModelKey = Literal["cnn14-32k", "cnn14-16k"]
TopK = Literal[5, 10, 15, 20]

DEFAULT_MODEL: ModelKey = "cnn14-32k"
DEFAULT_TOP_K: TopK = 10


class Label(BaseModel):
    label: str
    probability: float


class AudioMetadata(BaseModel):
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None


class TaggingSummary(BaseModel):
    """List-view projection of a Tagging (no embedding vector)."""

    audio_key: str
    tag_key: str
    model: str
    top_k: int
    labels: list[Label]
    tagged_at: datetime
    duration_seconds: float | None = None


class Tagging(TaggingSummary):
    """Full Tagging detail, including the embedding and its summary stats."""

    embedding: list[float]
    embedding_dim: int
    embedding_l2_norm: float
    source_metadata: AudioMetadata


class CreateTaggingRequest(BaseModel):
    audio_key: str = Field(..., description="Key of an ingested clip under audio/")
    model: ModelKey = DEFAULT_MODEL
    top_k: TopK = DEFAULT_TOP_K


class EditTaggingRequest(BaseModel):
    """Edit an existing Tagging. `audio_key` is the read-only identity."""

    audio_key: str
    model: ModelKey = DEFAULT_MODEL
    top_k: TopK = DEFAULT_TOP_K


class RunTaggingRequest(BaseModel):
    """Re-tag with the Tagging's stored parameters (no form)."""

    audio_key: str


class ManifestEntry(BaseModel):
    """One line of labels_index.jsonl — the dataset index for downstream jobs.

    `top_labels` carries the top-k labels *with* their probabilities, so a
    training/search job can consume the index without opening every per-clip tag
    JSON, and so the Taggings list and Dashboard read from this one cheap object.
    """

    audio_key: str
    tag_key: str
    model: str
    top_k: int
    top_labels: list[Label]
    tagged_at: datetime
    duration_seconds: float | None = None


class TopLabelCount(BaseModel):
    label: str
    count: int


class CorpusStats(BaseModel):
    """Aggregate dashboard metrics across the tagged corpus."""

    clips_ingested: int
    clips_tagged: int
    pct_tagged: float
    distinct_labels: int
    top_labels: list[TopLabelCount]
    recent_taggings: list[TaggingSummary]


class LibraryClip(BaseModel):
    """A clip under the sample-scoped audio/ prefix, with tag status."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    uploaded_at: datetime
    tagged: bool
    tag_key: str | None = None
    duration_seconds: float | None = None
