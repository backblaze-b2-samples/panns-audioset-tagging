<!-- last_verified: 2026-08-12 -->
# Feature: Ingest (audio upload)

## Purpose
Upload audio clips (WAV / FLAC / MP3) directly to Backblaze B2 under the
`audio/` prefix, where they become the corpus the Library and the tagging
pipeline operate on.

## Used By
- UI: `/upload` page — shown in the nav as **Ingest** (`UploadForm`, `Dropzone`)
- API: `POST /upload/presign`, `POST /upload/verify`

## Core Functions
- `apps/web/src/components/upload/upload-form.tsx` — the ingest form + queue
- `apps/web/src/lib/upload-file-types.ts` — client allow-list (mirrors the backend)
- `apps/web/src/lib/api-client.ts` — `uploadFile()` (presign → direct PUT → verify)
- `services/api/app/runtime/upload.py` — presign + verify handlers
- `services/api/app/service/upload.py` — `ALLOWED_TYPES`, key minting under `audio/`, signature sniffing
- `services/api/app/repo/b2_upload.py` — presigned PUT generation

## Canonical Files
- Direct-to-B2 upload flow: `services/api/app/service/upload.py`

## Inputs
- filename, content_type, size_bytes (declared at presign time)
- the file bytes (PUT directly to B2, never through the API)

## Outputs
- An object stored at `audio/<sanitized-filename>` in B2.
- `POST /upload/verify` → `FileUploadResponse`.

## Flow
- The browser declares the file → `POST /upload/presign` validates type/size and
  mints a key under `audio/`, returning a short-lived presigned PUT.
- The browser PUTs the bytes straight to B2 (size + content-type are signed into
  the URL, so B2 rejects a mismatch).
- `POST /upload/verify` heads the stored object and sniffs its leading bytes.
- The clip now appears in the Library, ready to tag.

## Edge Cases
- Disallowed type / extension mismatch → 415 at presign.
- Empty or oversize file → 400 / 413.
- Content bytes don't match the declared type → object deleted, 415 at verify.

## UX States
- Empty: dropzone prompt.
- Uploading: per-file progress.
- Error: inline per-file failure with the server reason.

## Verification
- Test files: `services/api/tests/test_upload_validation.py`, `services/api/tests/test_upload_conflict.py`
- Required cases: presign mints an `audio/` key, type/size rejection, signature mismatch deletes the object.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [Library / Explorer](file-browser.md)
- [Taggings](taggings.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
