# Build plan — `panns-audioset-tagging`

Scaffolded from `vibe-coding-starter-kit` (cloned fresh into
`.claude/scratch/vcsk-d2fb4542-b063-4cd5-ba70-91f560e3be7a/` — the ONLY source of truth).

## 1. Purpose

`panns-audioset-tagging` is a B2 sample that tags large collections of unlabeled
audio clips with **AudioSet** event labels using **PANNs** (Pretrained Audio
Neural Networks, `qiuqiangkong/audioset_tagging_cnn`) running **locally** — no
second API key, B2 credentials only. For each clip it produces a 527-class
AudioSet label-probability vector and a 2048-dim CNN embedding, extracts the
top-k labels, writes a per-clip tag JSON to B2 under `tags/`, and maintains a
`labels_index.jsonl` manifest that downstream training/search pipelines read via
the S3-compatible API. Audience: acoustic-monitoring teams, broadcast/media
archivists, and smart-home dataset builders who need to label big audio corpora
and index the results in object storage. The sample's real point is **B2 as the
storage layer for a bulk audio-ML workflow** — every artifact (source audio, tag
JSON, embedding, manifest) lives in B2 and is read back over S3.

## 2. Architecture delta from vibe-coding-starter-kit

The starter kit is the ceiling. Strip what an audio-tagging app doesn't need;
keep the whole B2/S3 spine, design system, and infra.

### KEEP (as-is or lightly renamed)
- Monorepo shape: `apps/web` (Next.js) + `services/api` (FastAPI) + `packages/shared` + `infra/`.
- The entire `services/api/app/repo/` B2 spine: `b2_client.py`, `b2_object.py`,
  `b2_upload.py`, `list_cache.py`, `counter.py` — boto3 stays confined here.
- **Full-bucket explorer** (`/files`, `file-browser.tsx`, `files-by-key/*` routes,
  `service/files.py`) — **NEVER removable** (non-negotiable keep). It is the app's
  raw-B2 window and stays in the nav as **Explorer**.
- All `components/ui/*` primitives, layout (`app-sidebar`, `header`,
  `command-palette`, `theme-provider`, `health-banner`), `settings/*`
  (the form-UX exemplar), design tokens, `globals.css`.
- Health/metrics/ratelimit runtime, CORS+middleware ordering in `main.py`,
  presigned-URL upload flow, list cache, `scripts/setup_b2_cors.py`, tests
  harness (`conftest.py`, structure/contract tests), `.github/`, `vercel.json`,
  `infra/`, pre-commit.

### TRIM (remove from starter)
- `/design` page + `components/design/*` + `docs/design-system.md` reference nav
  entry — design-system showcase is starter scaffolding, not part of this sample's
  story. (Keep the tokens/`globals.css` it documents; only drop the showcase page
  and its sidebar "Reference" group.)
- Image/PDF metadata extraction specifics in `service/metadata.py` +
  `docs/features/metadata-extraction.md` + `Pillow`/`PyPDF2` deps — replaced by
  **audio** metadata (duration / sample-rate / channels) via `soundfile`.
- Starter feature docs that no longer match: rewrite `dashboard.md`,
  `file-upload.md`, `file-browser.md`, `settings.md`; delete
  `metadata-extraction.md`.
- Starter README body (fully rewritten for this sample; keep structure/tone).

### ADD (new for panns-audioset-tagging)
- **Local PANNs tagging engine** — `services/api/app/service/tagging.py` (+ a thin
  `services/api/app/repo/panns_engine.py` that owns the `panns-inference` import,
  lazy model load, and device autodetect). Decodes audio (librosa/soundfile →
  32 kHz mono), runs `AudioTagging.inference()` → `clipwise_output` (527) +
  `embedding` (2048), extracts top-k AudioSet labels.
- **Tag artifact writer** — writes `tags/<audio_key>.json`
  (`{audio_key, model, top_k, labels:[{label,probability}], embedding:[...2048],
  embedding_dim, tagged_at}`) to B2 via the existing repo layer, then rebuilds the
  manifest.
- **Manifest builder** — `labels_index.jsonl` (one JSON line per tagged clip:
  `{audio_key, tag_key, top_labels, model, tagged_at}`), **rebuilt by listing
  `tags/`** after every create/edit/run/delete (idempotent; no read-modify-write
  race). Written to bucket root as `labels_index.jsonl`.
- **Sample-scoped asset explorer — "Library"** (REQUIRED add): a view scoped to
  the sample's own `audio/` prefix listing ingested clips with tag-status badges
  (Tagged / Untagged), duration, and a "Tag" action. This is the scoped
  counterpart to the always-kept full-bucket Explorer.
- **Taggings workspace** (primary-entity CRUD, see §4) — list + create + detail +
  edit + delete + run(re-tag).
- New API routes under `services/api/app/runtime/tagging.py` and
  `service/tagging.py` (list/create/get/update/delete/retag; manifest fetch;
  audio-metadata).
- Reskinned **Dashboard** (corpus stats: clips ingested, clips tagged, % tagged,
  distinct labels, top-labels distribution, recent taggings).
- Reskinned **Upload → "Ingest"** (uploads audio to `audio/`).

### Nav (final): Dashboard · Ingest · Library · Taggings · Explorer · Settings

## 3. B2 surface (S3-compatible only — no b2-native)

All via boto3 S3 client in `repo/` with the custom user-agent. No b2-native SDK.

| Operation | Used by |
|---|---|
| `put_object` | ingest audio → `audio/…`; write `tags/<key>.json`; write `labels_index.jsonl` |
| `get_object` | read audio bytes for tagging; read a tag JSON; read the manifest |
| `list_objects_v2` | Library (`audio/`), Explorer (bucket-wide), manifest rebuild (`tags/`), stats |
| `head_object` | clip/tag metadata |
| `delete_object` | delete a Tagging artifact (and, from Library, a source clip) |
| `generate_presigned_url` | audio playback (inline) + download; tag-JSON download |

No b2-native usage anywhere. Endpoint derived from `B2_REGION`
(`https://s3.{region}.backblazeb2.com`); `signature_version=s3v4`.

## 4. Key features (seed README + `docs/features/*`)

**Primary entity: `Tagging`** — the tag result produced by running PANNs over one
audio clip (backed by `tags/<audio_key>.json`). All five lifecycle verbs are
built in the UI (nothing omitted → `omitted_ui_verbs: []`):

- **create** — Taggings page "New tagging" form: pick an ingested clip, set
  `top_k` + `model`, run PANNs, write the tag JSON + manifest.
- **read** — Tagging detail: top-k labels as probability bars, embedding summary
  (dim = 2048, L2 norm, first-N sparkline), inline audio player (presigned),
  source audio metadata, link to the raw `tags/…json` object.
- **edit** — edit an existing Tagging's `top_k`/`model` (form pre-filled; `audio_key`
  is read-only identity); saving recomputes and overwrites the tag JSON.
- **delete** — remove the Tagging artifact + its manifest line (confirm via
  `alert-dialog`; source clip is preserved).
- **run** — one-click **Re-tag** (no form) recomputes the tag JSON with the stored
  params; useful after a model refresh or re-ingest.

**Feature bullets (README / `docs/features/` stubs):**
1. Local PANNs AudioSet tagging — 527-class probabilities + 2048-dim embedding per clip, top-k label extraction, CPU by default.
2. Bulk audio ingest to B2 under `audio/…` (WAV/FLAC/MP3), organized by prefix.
3. Per-clip tag artifacts written to `tags/…json` alongside the audio.
4. `labels_index.jsonl` manifest as a fast dataset index for training/search jobs.
5. Library (sample-scoped audio explorer) + full-bucket Explorer, both over S3.
6. Corpus dashboard: tagged coverage + top-label distribution across the collection.

### External API provider
**None.** PANNs runs fully on-device (the description: "Runs on local OSS — no
second API key, B2 credentials only"). Per `api-provider-selection.md` step 1/2
this feature is **core + on-device**, so LOCAL is the default with no remote path.

- feature: **PANNs AudioSet tagging**
  - provider/model: PANNs **Cnn14** pretrained checkpoint (via the `panns-inference`
    package; also exposes the 16 kHz **Cnn14_16k** variant).
  - **deployment: local**
  - est. cost for one full demo run: **$0** (no external API; B2 storage only;
    model checkpoint auto-downloads once to `~/panns_data`, ~300 MB).
  - env var for key: **none** (B2 credentials only).
  - **CPU-default / GPU-autodetect (hard rule):** select device
    `cuda` if `torch.cuda.is_available()` else `cpu`. **MPS caveat:**
    `panns-inference` hard-codes `cuda`/`cpu` and has no MPS path, so on Apple
    silicon it falls back to **CPU** (documented; do not force MPS). Never
    hard-require a GPU.

### Provider orchestration via Genblaze
**Not applicable** — the description's suggested stack does not mention Genblaze,
and there is no external AI provider to route. All inference is the local PANNs
engine. Do **not** add `genblaze-*` packages.

### Form UX conventions (create/edit Tagging forms)
Reuse `settings-form.tsx` patterns (react-hook-form + zod + `Select`/`RadioGroup`
+ `FormDescription`). Finite-value fields use selectors, never free text:
- `model` → **Select**: `cnn14-32k` (default) · `cnn14-16k`.
- `top_k` → **Select** (or segmented `RadioGroup`): `5` · `10` (default) · `15` · `20`.
- `audio_key` (create only) → **Select** populated from the Library (ingested
  clips); on edit it is read-only (the Tagging's identity).
- **Create-form default hints** (placeholder / `FormDescription`, guidance only —
  never an autofill button): model → "Cnn14 (32 kHz) — best general accuracy";
  top_k → "10 labels is a good default"; audio_key → hint to pick a clip from the
  Library (first available).

## 5. Doc transforms
- **Rewrite:** `docs/features/dashboard.md` (corpus/tagging stats),
  `file-upload.md` (audio ingest to `audio/`), `file-browser.md` (Explorer +
  Library split), `settings.md` (unchanged behavior; refresh copy).
- **New stubs (from `_template.md`):** `docs/features/audio-tagging.md`
  (PANNs engine, device autodetect, tag JSON schema), `docs/features/taggings.md`
  (primary-entity CRUD+run), `docs/features/labels-index.md` (manifest format &
  how training jobs consume it).
- **Delete:** `docs/features/metadata-extraction.md`.
- Refresh `README.md`, `ARCHITECTURE.md`, `PRODUCT.md`, `AGENTS.md`,
  `docs/app-workflows.md` to the audio-tagging workflow. Keep `docs/SECURITY.md`,
  `RELIABILITY.md`, `dev-workflows.md` structure; adjust only what changed
  (env-var names, deps, endpoints).
- Move this plan to `docs/exec-plans/completed/initial-scaffold.md` on PASS.

## 6. Rename table

| Dimension | vibe-coding-starter-kit | panns-audioset-tagging |
|---|---|---|
| kebab / repo | `vibe-coding-starter-kit` | `panns-audioset-tagging` |
| snake | `vibe_coding_starter_kit` | `panns_audioset_tagging` |
| Title Case | "Vibe Coding Starter Kit" | "PANNs AudioSet Tagging" |
| `APP_NAME` (`lib/app-config.ts`) | "Vibe Coding Starter Kit" | "PANNs AudioSet Tagging" |
| `APP_DESCRIPTION` | "File management dashboard template…" | "Tag audio collections with AudioSet labels + embeddings, stored on Backblaze B2" |
| API_TITLE / desc (`main.py`) | "Vibe Coding Starter Kit API" | "PANNs AudioSet Tagging API" |
| root `package.json` name | `vibe-coding-starter-kit` | `panns-audioset-tagging` |
| `apps/web` pkg name | (starter) | `panns-audioset-tagging-web` |
| `packages/shared` name | (starter) | `@panns-audioset-tagging/shared` (match starter scope pattern) |
| `services/api` pyproject name | (starter) | `panns-audioset-tagging-api` |
| user-agent (`user_agent_extra`, 2 files) | `b2ai-oss-start` | `panns-audioset-tagging` |
| brand slug in README / `scripts/doctor.mjs` / `app-sidebar.tsx` UTM / `b2_client.py` / `setup_b2_cors.py` | `b2ai-oss-start` | `panns-audioset-tagging` |
| UTM `utm_content` (sidebar footer) | `b2ai-oss-start` | `panns-audioset-tagging` |
| `.github/` workflow slugs referencing the name | (starter) | `panns-audioset-tagging` |

### Env-var rename → **Standard #3** (parent CLAUDE.md; starter deviates)
Rename across `settings.py`, `main.py` (`REQUIRED_B2_SETTINGS` + placeholders),
`.env.example`, `setup_b2_cors.py`, README, and docs:

| Starter | Standard #3 (use this) |
|---|---|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (same) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (same) |
| `B2_ENDPOINT` | derive from **`B2_REGION`** → `https://s3.{B2_REGION}.backblazeb2.com` |
| `B2_PUBLIC_URL` | `B2_PUBLIC_URL_BASE` |

`settings.py`: add `b2_application_key_id`, `b2_region` (default e.g.
`us-west-004`), `b2_public_url_base`; compute `b2_endpoint` as a property from
`b2_region`. Update every reader (`b2_client.py`, `main.py`, health, CORS script).

## Dependency pins (avoid the unpinned-ML clean-install trap)
Bounded pins in `services/api/requirements.txt` (regen `requirements.lock`):
`panns-inference==0.1.1`, `torch>=2.2,<2.5`, `torchlibrosa>=0.1.0`,
`librosa>=0.10,<0.11`, `soundfile>=0.12`, `numpy>=1.24,<2.0` (numba/librosa
compat), `numba>=0.58`. Drop `Pillow`/`PyPDF2`. Keep fastapi/uvicorn/boto3/
pydantic stack. Model load + inference are **lazy** (first tag request), so
`pytest` and `pnpm build` stay green without torch downloading the checkpoint —
tests mock the PANNs engine at the `repo/panns_engine.py` boundary. MP3 decode is
best-effort via `soundfile`/libsndfile; WAV/FLAC are guaranteed. Note in README
that the first tag run downloads the ~300 MB checkpoint.

## Non-negotiables checklist (reviewer will gate on these)
- [ ] S3 API only (no b2-native).
- [ ] Custom user-agent `panns-audioset-tagging` on **every** S3 client.
- [ ] Standard #3 `B2_*` env names everywhere.
- [ ] Full-bucket Explorer kept **and** sample-scoped Library added.
- [ ] All 5 primary-entity verbs (create/read/edit/delete/run) in the UI.
- [ ] Selectors for finite fields; create-form default hints as guidance.
- [ ] CPU-default + GPU autodetect; no hard GPU requirement.
- [ ] Pinned ML deps; lazy model load; tests mock the engine.
