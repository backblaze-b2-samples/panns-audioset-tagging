<!-- last_verified: 2026-08-12 -->
# Feature: Library & Explorer

Two complementary views over the same B2 bucket.

## Purpose
- **Library** (`/library`) — a sample-scoped view of the ingested audio corpus
  (the `audio/` prefix) with per-clip tag status, duration, and a one-click Tag
  action.
- **Explorer** (`/files`) — the raw, full-bucket window into B2: every object,
  including `audio/`, per-clip `tags/…json`, and the `labels_index.jsonl`
  manifest. This is the starter kit's always-kept file browser.

## Used By
- UI: `/library` (`LibraryBrowser`), `/files` (`FileBrowser`)
- API: `GET /library`; `GET /files`, `GET /files-by-key/*`

## Core Functions
- `apps/web/src/components/library/library-browser.tsx` — audio-scoped list + Tag action
- `apps/web/src/components/files/file-browser.tsx` — full-bucket tree/preview
- `apps/web/src/components/files/file-metadata-panel.tsx` — on-demand detail (checksums + audio metadata)
- `services/api/app/runtime/tagging.py` — `GET /library`
- `services/api/app/service/tagging.py` — `get_library()` (lists `audio/`, cross-references the manifest)
- `services/api/app/service/files.py` — full-bucket listing + on-demand `extract_metadata()`

## Inputs
- Library: none (lists `audio/`).
- Explorer: optional prefix; a key for by-key detail/preview/download.

## Outputs
- `GET /library` → `LibraryClip[]` (`key`, `filename`, `size`, `uploaded_at`, `tagged`, `tag_key`, `duration_seconds`).
- `GET /files-by-key/detail` → `FileMetadataDetail` (checksums + audio duration / sample-rate / channels).

## Flow
- Library lists `audio/`, reads `labels_index.jsonl` once for tag status +
  duration, and renders a badge (`Tagged` / `Untagged`) per clip. The Tag button
  runs a default tagging (`cnn14-32k`, top-k 10) via `POST /taggings`.
- Explorer paginates the whole bucket; clicking an object previews it and can
  recompute rich metadata on demand.

## Edge Cases
- Library empty (nothing ingested) → empty state pointing at Ingest.
- Duration only known for tagged clips (read from the manifest); untagged clips show `—`.
- Explorer detail for a non-audio object → checksums only, no audio section.

## UX States
- Loading: skeleton rows.
- Empty: Library CTA to Ingest; Explorer empty-bucket message.
- Loaded: clip/object tables.

## Verification
- Test files: `services/api/tests/test_tagging.py` (Library), `services/api/tests/test_file_detail.py` (Explorer detail)
- Required cases: tag-status badge derived from the manifest; audio metadata extraction.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [Ingest](file-upload.md)
- [Taggings](taggings.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
