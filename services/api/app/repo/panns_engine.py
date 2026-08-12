"""Local PANNs (Pretrained Audio Neural Networks) AudioSet tagging engine.

This module is the ONLY place that imports `panns-inference` / `torch` / `librosa`,
mirroring the way boto3 is confined to the rest of `repo/`. Every heavy import is
deliberately *lazy* (inside functions, never at module top) so that pytest
collection and `from app.main import app` never pull in torch or download the
~300 MB model checkpoint. The model is loaded as a process-wide singleton on the
first tag request.

Device selection is CPU-by-default with GPU autodetect: `cuda` when
`torch.cuda.is_available()` else `cpu`. `panns-inference` hard-codes a
`cuda`/`cpu` split and has no Apple MPS path, so on Apple silicon this engine
runs on **CPU** (documented; we never force MPS and never hard-require a GPU).

The upstream package downloads its label CSV and checkpoint via `os.system("wget ...")`,
which fails on machines without `wget`. We therefore pre-fetch both artifacts with
the Python stdlib (`urllib`) into `~/panns_data` before importing the package, so the
engine is self-contained and needs no system tools.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# All PANNs artifacts (label CSV + checkpoints) live here, matching the path the
# upstream `panns-inference` package expects.
PANNS_DATA_DIR = Path.home() / "panns_data"
LABELS_CSV_PATH = PANNS_DATA_DIR / "class_labels_indices.csv"
LABELS_CSV_URL = (
    "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/"
    "class_labels_indices.csv"
)


@dataclass(frozen=True)
class ModelSpec:
    """A selectable PANNs Cnn14 variant.

    `model_kwargs` is None for the default 32 kHz Cnn14 (upstream `AudioTagging`
    builds exactly that internally); for the 16 kHz variant we construct the same
    Cnn14 architecture with the 16 kHz spectrogram front-end and point it at the
    16 kHz checkpoint.
    """

    key: str
    sample_rate: int
    checkpoint_filename: str
    checkpoint_url: str
    model_kwargs: dict | None = field(default=None)

    @property
    def checkpoint_path(self) -> Path:
        return PANNS_DATA_DIR / self.checkpoint_filename


MODEL_SPECS: dict[str, ModelSpec] = {
    "cnn14-32k": ModelSpec(
        key="cnn14-32k",
        sample_rate=32000,
        checkpoint_filename="Cnn14_mAP=0.431.pth",
        checkpoint_url=(
            "https://zenodo.org/record/3987831/files/"
            "Cnn14_mAP%3D0.431.pth?download=1"
        ),
        model_kwargs=None,
    ),
    "cnn14-16k": ModelSpec(
        key="cnn14-16k",
        sample_rate=16000,
        checkpoint_filename="Cnn14_16k_mAP=0.438.pth",
        checkpoint_url=(
            "https://zenodo.org/record/3987831/files/"
            "Cnn14_16k_mAP%3D0.438.pth?download=1"
        ),
        # Same Cnn14 architecture, 16 kHz spectrogram front-end.
        model_kwargs={
            "sample_rate": 16000,
            "window_size": 512,
            "hop_size": 160,
            "mel_bins": 64,
            "fmin": 50,
            "fmax": 8000,
            "classes_num": 527,
        },
    ),
}

DEFAULT_MODEL = "cnn14-32k"
EMBEDDING_DIM = 2048
NUM_CLASSES = 527

# Process-wide singletons. Loading a Cnn14 checkpoint is expensive, so each
# selected variant is loaded once and reused across requests.
_models: dict[str, object] = {}
_models_lock = Lock()
_labels_cache: list[str] | None = None


class ModelUnavailableError(RuntimeError):
    """Raised when a requested model key is not a known PANNs variant."""


def available_models() -> list[str]:
    return list(MODEL_SPECS.keys())


def _download(url: str, dest: Path) -> None:
    """Stream `url` to `dest` using only the stdlib (no `wget`, no `requests`).

    Downloads to a `.part` sidecar first and atomically renames on success so an
    interrupted download never leaves a truncated file that later reads as valid.
    """
    import shutil
    import urllib.request

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    logger.info("Downloading PANNs artifact: %s -> %s", url, dest)
    request = urllib.request.Request(
        url, headers={"User-Agent": "panns-audioset-tagging"}
    )
    with urllib.request.urlopen(request) as response, open(tmp, "wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(dest)


def _ensure_labels_csv() -> None:
    """Make sure the 527-class AudioSet label CSV exists before importing PANNs.

    Importing `panns_inference` reads this CSV at module import time; without it
    the upstream package tries to `wget` it and crashes on a wget-less machine.
    """
    if LABELS_CSV_PATH.exists() and LABELS_CSV_PATH.stat().st_size > 0:
        return
    _download(LABELS_CSV_URL, LABELS_CSV_PATH)


def _ensure_checkpoint(spec: ModelSpec) -> None:
    """Ensure the model checkpoint (~300 MB) is present locally.

    Uses a size floor so a previous truncated download is re-fetched rather than
    loaded and failing deep inside torch.
    """
    path = spec.checkpoint_path
    if path.exists() and path.stat().st_size > 100_000_000:
        return
    _download(spec.checkpoint_url, path)


def _read_labels() -> list[str]:
    """Return the 527 AudioSet display names, indexed to match model output."""
    global _labels_cache
    if _labels_cache is not None:
        return _labels_cache
    import csv

    _ensure_labels_csv()
    with open(LABELS_CSV_PATH, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    # CSV columns: index, mid, display_name. Row order matches model output order.
    _labels_cache = [row[2] for row in rows[1:] if len(row) >= 3]
    return _labels_cache


def _select_device() -> str:
    """CPU by default; use CUDA only when a GPU is actually present.

    `panns-inference` has no Apple MPS path, so Apple silicon resolves to CPU.
    """
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _get_model(model_key: str):
    """Lazily load (and cache) the PANNs AudioTagging model for `model_key`."""
    spec = MODEL_SPECS.get(model_key)
    if spec is None:
        raise ModelUnavailableError(
            f"Unknown model '{model_key}'. Choose one of {available_models()}."
        )

    with _models_lock:
        cached = _models.get(model_key)
        if cached is not None:
            return cached

        _ensure_labels_csv()
        _ensure_checkpoint(spec)

        # Imported here (not at module top) so torch/panns stay out of test
        # collection and out of `from app.main import app`.
        from panns_inference import AudioTagging
        from panns_inference.models import Cnn14

        device = _select_device()
        logger.info("Loading PANNs model '%s' on device=%s", model_key, device)
        if spec.model_kwargs is None:
            model = AudioTagging(
                checkpoint_path=str(spec.checkpoint_path), device=device
            )
        else:
            cnn = Cnn14(**spec.model_kwargs)
            model = AudioTagging(
                model=cnn,
                checkpoint_path=str(spec.checkpoint_path),
                device=device,
            )
        _models[model_key] = model
        return model


def _decode_audio(audio_bytes: bytes, target_sr: int):
    """Decode arbitrary audio bytes to a mono float32 waveform at `target_sr`.

    WAV/FLAC are guaranteed (libsndfile); MP3 is best-effort via the same stack.
    """
    import io

    import librosa

    waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=target_sr, mono=True)
    return waveform.astype("float32")


def tag_audio(audio_bytes: bytes, *, model_key: str, top_k: int) -> dict:
    """Run PANNs over one clip and return its top-k labels and full embedding.

    Returns a plain dict (no torch/numpy types leak out):
      - labels: [{label, probability}] sorted by probability desc, length top_k
      - embedding: list[float] length 2048
      - embedding_dim: int (2048)
      - model, top_k, sample_rate: the parameters actually used
    """
    spec = MODEL_SPECS.get(model_key)
    if spec is None:
        raise ModelUnavailableError(
            f"Unknown model '{model_key}'. Choose one of {available_models()}."
        )

    waveform = _decode_audio(audio_bytes, spec.sample_rate)
    model = _get_model(model_key)
    # AudioTagging.inference expects a (batch, samples) array.
    clipwise_output, embedding = model.inference(waveform[None, :])

    probabilities = clipwise_output[0]
    embedding_vector = embedding[0]
    labels = _read_labels()

    order = probabilities.argsort()[::-1][: max(1, top_k)]
    top_labels = [
        {"label": labels[int(i)], "probability": float(probabilities[int(i)])}
        for i in order
    ]

    return {
        "labels": top_labels,
        "embedding": [float(x) for x in embedding_vector.tolist()],
        "embedding_dim": int(embedding_vector.shape[0]),
        "model": model_key,
        "top_k": int(top_k),
        "sample_rate": spec.sample_rate,
    }
