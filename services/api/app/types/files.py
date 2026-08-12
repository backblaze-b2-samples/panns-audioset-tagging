from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
    # Set when the audio extractor was skipped or failed (e.g. a non-audio
    # object, or a clip whose header could not be read). The core fields above
    # are always present, so the UI shows this instead of silently dropping the
    # Audio section.
    metadata_warning: str | None = None
    # Audio-specific (read from the clip header via soundfile).
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
