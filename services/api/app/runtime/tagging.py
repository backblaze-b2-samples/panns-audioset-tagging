import logging

# Sync `def` handlers on purpose: the whole chain is blocking (boto3 + a
# CPU-bound torch forward pass). Starlette runs sync handlers in its threadpool,
# so one slow tag request doesn't stall the event loop (see runtime/files.py).
from fastapi import APIRouter, HTTPException

from app.repo.panns_engine import ModelUnavailableError
from app.service.tagging import (
    TaggingError,
    create_tagging,
    delete_tagging,
    edit_tagging,
    get_corpus_stats,
    get_library,
    get_manifest,
    get_tagging,
    list_taggings,
    run_tagging,
)
from app.types import (
    CorpusStats,
    CreateTaggingRequest,
    EditTaggingRequest,
    LibraryClip,
    ManifestEntry,
    RunTaggingRequest,
    Tagging,
    TaggingSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# SECURITY: like the Files routes, these are intentionally UNAUTHENTICATED and
# bucket-wide (single-tenant demo stance — see docs/SECURITY.md). A multi-tenant
# clone must add auth here AND scope audio/ + tags/ to the caller's own prefixes.


def _tagging_or_http(fn, *args) -> Tagging:
    """Run a service call that returns a Tagging, mapping errors to HTTP codes."""
    try:
        return fn(*args)
    except ModelUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except TaggingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Storage error while tagging"
        ) from None


@router.get("/taggings", response_model=list[TaggingSummary])
def list_taggings_endpoint():
    try:
        return list_taggings()
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read taggings from storage"
        ) from None


@router.post("/taggings", response_model=Tagging)
def create_tagging_endpoint(req: CreateTaggingRequest):
    return _tagging_or_http(create_tagging, req.audio_key, req.model, req.top_k)


@router.get("/taggings/detail", response_model=Tagging)
def get_tagging_endpoint(audio_key: str):
    return _tagging_or_http(get_tagging, audio_key)


@router.post("/taggings/edit", response_model=Tagging)
def edit_tagging_endpoint(req: EditTaggingRequest):
    return _tagging_or_http(edit_tagging, req.audio_key, req.model, req.top_k)


@router.post("/taggings/run", response_model=Tagging)
def run_tagging_endpoint(req: RunTaggingRequest):
    return _tagging_or_http(run_tagging, req.audio_key)


@router.delete("/taggings")
def delete_tagging_endpoint(audio_key: str):
    try:
        delete_tagging(audio_key)
    except TaggingError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to delete tagging"
        ) from None
    logger.info("Tagging deleted: audio_key=%s", audio_key)
    return {"deleted": True, "audio_key": audio_key}


@router.get("/taggings/manifest", response_model=list[ManifestEntry])
def get_manifest_endpoint():
    return get_manifest()


@router.get("/taggings/stats", response_model=CorpusStats)
def corpus_stats_endpoint():
    try:
        return get_corpus_stats()
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read corpus stats"
        ) from None


@router.get("/library", response_model=list[LibraryClip])
def library_endpoint():
    try:
        return get_library()
    except RuntimeError:
        raise HTTPException(
            status_code=502, detail="Failed to read the audio library"
        ) from None
