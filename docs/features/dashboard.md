<!-- last_verified: 2026-08-12 -->
# Feature: Dashboard

## Purpose
Give an at-a-glance view of the tagged audio corpus: how much has been ingested,
how much is tagged, and what AudioSet labels dominate the collection.

## Used By
- UI: `/` page (`CorpusDashboard`)
- API: `GET /taggings/stats`

## Core Functions
- `apps/web/src/components/dashboard/corpus-dashboard.tsx` — stat cards, top-label bars, recent taggings
- `apps/web/src/lib/queries.ts` — `useCorpusStats()`
- `apps/web/src/lib/api-client.ts` — `getCorpusStats()`
- `services/api/app/runtime/tagging.py` — `GET /taggings/stats` handler
- `services/api/app/service/tagging.py` — `get_corpus_stats()` aggregation
- `services/api/app/repo/b2_client.py` — `list_files()` over `audio/` + the manifest read

## Canonical Files
- Dashboard layout: `apps/web/src/components/dashboard/corpus-dashboard.tsx`
- Stats service logic: `services/api/app/service/tagging.py`

## Inputs
- None (loads automatically).

## Outputs
- `GET /taggings/stats` → `CorpusStats`:
  - `clips_ingested` — objects under `audio/`
  - `clips_tagged` — distinct audio keys present in `labels_index.jsonl`
  - `pct_tagged` — coverage %
  - `distinct_labels` — count of distinct labels across the manifest's top-k
  - `top_labels` — the 10 most frequent labels with counts
  - `recent_taggings` — the 5 most recent taggings (summary)

## Flow
- Page loads → `useCorpusStats()` calls `GET /taggings/stats`.
- The service lists `audio/` (clip count) and reads `labels_index.jsonl` once (a
  single cheap object), then aggregates coverage + label frequencies in memory.
- Cards, the top-label distribution, and the recent-taggings list render.

## Edge Cases
- No clips ingested → empty state pointing at Ingest.
- Clips ingested but none tagged → 0% coverage, empty top-labels message.
- Manifest missing → treated as "no taggings yet" (empty), never an error.
- API unavailable → error state with retry.

## UX States
- Loading: four skeleton stat cards.
- Empty: "No audio ingested yet" with an Ingest CTA.
- Loaded: stat cards + top-label bars + recent taggings.

## Verification
- Test files: `services/api/tests/test_tagging.py`
- Required cases: coverage math (`pct_tagged`), distinct-label count, empty corpus.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
- [Taggings](taggings.md)
- [Labels index](labels-index.md)
