<!-- last_verified: 2026-08-12 -->
# Feature: Taggings (primary entity)

## Purpose
The primary entity of this sample: a `Tagging` is the result of running PANNs
over one audio clip, persisted as `tags/<audio_key>.json` in B2. The Taggings
workspace exposes all five lifecycle verbs.

## Used By
- UI: `/taggings` page (`TaggingsWorkspace`, `TaggingForm`, `TaggingDetailDialog`)
- API: `GET/POST/DELETE /taggings`, `GET /taggings/detail`, `POST /taggings/edit`, `POST /taggings/run`

## Core Functions
- `apps/web/src/components/taggings/taggings-workspace.tsx` — list + all five verbs
- `apps/web/src/components/taggings/tagging-form.tsx` — create/edit form (selectors + hints)
- `apps/web/src/components/taggings/tagging-detail-dialog.tsx` — probability bars, embedding summary, audio player
- `apps/web/src/lib/queries.ts` — `useTaggings`, `useTaggingDetail`, `useCreate/Edit/Run/DeleteTagging`
- `services/api/app/service/tagging.py` — orchestration + manifest rebuild
- `services/api/app/runtime/tagging.py` — routes

## Canonical Files
- Service orchestration: `services/api/app/service/tagging.py`
- Form-UX exemplar: `apps/web/src/components/taggings/tagging-form.tsx`

## Inputs
- create/edit: `audio_key` (Select from Library on create; read-only on edit), `model` (Select), `top_k` (Select)
- run/delete/detail: `audio_key`

## Outputs
- `tags/<audio_key>.json` — `{audio_key, model, top_k, labels, embedding, embedding_dim, tagged_at, source_metadata}`
- A rebuilt `labels_index.jsonl` manifest after every write.
- `GET /taggings/detail` → `Tagging` (with the full embedding + L2 norm).

## The five verbs
- **create** — pick an ingested clip, set model + top_k, run PANNs, write the tag JSON.
- **read** — detail dialog: top-k probability bars, embedding summary (dim 2048, L2 norm, first-64 sparkline), inline audio player (presigned URL), source metadata, link to the raw `tags/…json`.
- **edit** — change `model`/`top_k` (clip is read-only identity); recompute + overwrite.
- **delete** — remove the tag JSON + its manifest line (alert-dialog confirm); source clip kept.
- **run** — one-click Re-tag with the stored params.

## Form UX
- Finite fields use selectors: `model` = Select {cnn14-32k default, cnn14-16k}; `top_k` = Select {5,10 default,15,20}; `audio_key` = Select from the Library.
- Create-form default hints are guidance only (`FormDescription` / placeholder), never an autofill button.

## Edge Cases
- Missing clip → 404. Unknown model → 400. Undecodable audio → 422.
- `run` on a clip with no existing tagging → 404.
- Invalid `top_k` (not in the allowed set) → 422 (validated by the request model).

## Verification
- Test files: `services/api/tests/test_tagging.py`
- Required cases: create→read→list→library, edit changes params, run reuses stored params, delete removes the manifest line, invalid top_k rejected.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [Audio tagging engine](audio-tagging.md)
- [Labels index](labels-index.md)
- [App Workflows](../app-workflows.md)
