<!-- last_verified: 2026-08-12 -->
# App Workflows

User journeys inside the application. The core loop is **Ingest → Library → Tag →
consume the manifest**.

## Ingest audio

- User navigates to `/upload` (labelled **Ingest**)
- Drops or selects audio clips (WAV / FLAC / MP3) in the dropzone
- Client validates file size (max 100MB) and type
- Clips upload **directly from the browser to B2** (a presigned PUT) into the `audio/` prefix. A determinate progress bar tracks the bytes leaving the browser; once sent the row switches to "Verifying upload..." while the API HEADs and magic-byte-sniffs the stored object
- On success: toast notification and a green checkmark. The clip now appears in the Library
- On failure: red status icon with error message
- See: [Ingest](features/file-upload.md)

## Browse the Library and tag a clip

- User navigates to `/library`
- The page lists clips under `audio/` with a **Tagged / Untagged** badge, duration (for tagged clips, from the manifest), and size
- For an untagged clip, clicking **Tag** runs a default tagging (`cnn14-32k`, top-k 10) — the first run downloads the ~300 MB Cnn14 checkpoint and runs on CPU by default
- Tagged clips link through to the Taggings workspace
- Empty state points at Ingest
- See: [Library & Explorer](features/file-browser.md)

## Work with Taggings (the primary entity)

- User navigates to `/taggings`
- **Create**: "New tagging" opens a form — pick an ingested clip (Select from the Library), a model (Select: cnn14-32k default / cnn14-16k), and top-k (Select: 5/10/15/20). Submitting runs PANNs, writes `tags/<audio_key>.json`, and rebuilds the manifest
- **Read**: the detail dialog shows the top-k labels as probability bars, an embedding summary (dim 2048, L2 norm, first-64 sparkline), an inline audio player (presigned URL), source metadata, and a link to the raw tag JSON
- **Edit**: change the model/top-k (the clip is read-only identity) and re-run
- **Delete**: an alert-dialog confirms; the tag JSON and its manifest line are removed, the source clip is kept
- **Re-tag (run)**: one click recomputes with the stored parameters
- See: [Taggings](features/taggings.md)

## Explore the full bucket

- User navigates to `/files` (labelled **Explorer**) — the raw, full-bucket window into B2: `audio/`, `tags/…json`, and `labels_index.jsonl`
- Clicking an object opens its preview; the metadata panel shows checksums and, for audio, duration / sample-rate / channels
- Preview / download / delete work per object
- See: [Library & Explorer](features/file-browser.md)

## View the corpus Dashboard

- User navigates to `/` (home)
- `GET /taggings/stats` loads coverage + label distribution from the manifest
- Stat cards show: clips ingested, clips tagged, % tagged, distinct labels
- A top-label distribution and a recent-taggings list render below
- Empty state points at Ingest when nothing is ingested yet
- See: [Dashboard](features/dashboard.md)

## Change Preferences

- User navigates to `/settings`
- A banner at the top states that the page is mostly a demonstration: only Theme is wired up for real, the rest showcases what a settings page can look like when you adapt the kit
- **Theme** (real): editing it and saving applies it immediately and persists it (`next-themes`), and the header's theme toggle drives the same state
- **Profile and preference fields** (demo): Display name, Bio, Default file view (Tree/List/Grid), Email me on every upload, Warn me when approaching quota + threshold. Each is labelled "Demo field", persists to `localStorage` only, and drives no behaviour — there is no account system, mailer, quota banner, activity log, or List/Grid view behind them yet
- Saving reports honestly: a success toast that separates the real theme change from the locally-stored demo values, or a warning toast if the browser blocked storage (theme still changes). It never claims a save that did not happen — the original page toasted "Settings saved" for fields that changed nothing
- Danger Zone actions are a demo — no real delete runs
- See: [Settings](features/settings.md)
