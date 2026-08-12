import hashlib
import io
import logging
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


_AUDIO_WARNING = (
    "Audio metadata unavailable — the clip's header could not be read (the "
    "format may be unsupported or the file truncated). Checksums and size are "
    "still exact."
)


def probe_audio(file_data: bytes) -> dict:
    """Read duration / sample-rate / channels from an audio clip's header.

    Uses `soundfile` (lazy import), which reads only the container header for
    WAV/FLAC rather than decoding the whole clip. MP3 is best-effort via the
    same libsndfile stack. Returns a ``metadata_warning`` (and no numeric
    fields) when the header cannot be read, so the detail payload never silently
    omits the Audio section.
    """
    try:
        import soundfile as sf

        with sf.SoundFile(io.BytesIO(file_data)) as clip:
            frames = clip.frames
            sample_rate = clip.samplerate
            channels = clip.channels
        duration = frames / sample_rate if sample_rate else None
        return {
            "duration_seconds": duration,
            "sample_rate": sample_rate,
            "channels": channels,
        }
    except Exception:
        logger.warning("Audio metadata extraction failed", exc_info=True)
        return {"metadata_warning": _AUDIO_WARNING}


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
    uploaded_at: datetime | None = None,
) -> FileMetadataDetail:
    """Compute rich metadata from raw file bytes.

    Checksums, size, and extension are computed for every object. Audio clips
    additionally get duration / sample-rate / channels from their header. Other
    content types carry no format-specific fields and no warning.

    `uploaded_at` is the object's real upload time; callers recomputing metadata
    for an already-stored object MUST pass it (from head_object's LastModified)
    so the panel shows the true upload time rather than the recompute time. It
    defaults to now only for the fresh-upload path, where the two coincide.
    """
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    extra: dict = {}
    if content_type.startswith("audio/"):
        extra = probe_audio(file_data)

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=uploaded_at if uploaded_at is not None else datetime.now(UTC),
        **extra,
    )
