# Tech debt

Backlog of low-severity nitpicks surfaced during verification. These do not block
the marquee flow; fix opportunistically.

## 2026-08-12 — verify

- Taggings detail (inline audio player) — the native `<audio>` control reads `0:00 / 0:00` while the metadata row correctly shows the clip duration (e.g. 12.0s) → duration is not preloaded on the control; add `preload="metadata"` (or set duration from the known value) so the readout matches (shot `.local/verify/B/11-tagging-detail.png`).
- Ingest upload error summary — rejecting an unsupported file shows "1 file need attention" → subject/verb agreement ("need" → "needs"), pluralize by count (shot `.local/verify/B/05-upload-error-unsupported.png`).
- `services/api/app/repo/panns_engine.py::_ensure_checkpoint` — the checkpoint validity guard uses a fixed 100 MB size floor, but the `cnn14-16k` checkpoint is ~358 MB → a truncated-but-over-100 MB checkpoint left at the final path (e.g. after an interrupted download) passes the floor and never re-downloads, so the engine can't self-heal and every subsequent tag fails with a torch "unexpected EOF" until the file is deleted by hand. Prefer validating against the per-model expected size (or a `.part`→atomic-rename that never leaves a partial at the final path) instead of a single global floor. Contained/inferred, default `cnn14-32k` path unaffected (no UI shot — Lens C incidental, entangled with a host idle-sleep during download).
