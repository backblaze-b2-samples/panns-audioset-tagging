<!-- last_verified: 2026-08-12 -->
# Feature: Local PANNs AudioSet tagging engine

## Purpose
Tag an audio clip locally with PANNs (Pretrained Audio Neural Networks,
`qiuqiangkong/audioset_tagging_cnn`): a 527-class AudioSet probability vector and
a 2048-dim CNN embedding, with the top-k labels extracted. No second API key —
inference runs on-device.

## Used By
- API: `POST /taggings`, `POST /taggings/edit`, `POST /taggings/run` (via the tagging service)
- Engine: `services/api/app/repo/panns_engine.py`

## Core Functions
- `services/api/app/repo/panns_engine.py`:
  - `tag_audio(audio_bytes, model_key, top_k)` — decode → inference → top-k + embedding
  - `_get_model()` — lazy, cached model load per variant
  - `_select_device()` — CPU by default, CUDA when available (no MPS path)
  - `_ensure_labels_csv()` / `_ensure_checkpoint()` — self-contained artifact downloads

## Canonical Files
- Engine boundary: `services/api/app/repo/panns_engine.py` (the ONLY module that imports `panns-inference` / `torch` / `librosa`)

## Inputs
- `audio_bytes`: raw clip bytes (read from B2)
- `model_key`: `cnn14-32k` (default) or `cnn14-16k`
- `top_k`: 5 | 10 | 15 | 20

## Outputs
- `{ labels: [{label, probability}], embedding: float[2048], embedding_dim, model, top_k, sample_rate }`

## Flow
- Decode the clip to mono float32 at the model's sample rate (32 kHz or 16 kHz)
  via librosa/soundfile.
- Lazily load the Cnn14 checkpoint (downloaded once to `~/panns_data`, ~300 MB)
  onto the auto-detected device.
- Run `AudioTagging.inference()` → `clipwise_output` (527) + `embedding` (2048).
- Map the 527 probabilities to AudioSet display names and return the top-k.

## Edge Cases
- Unknown `model_key` → `ModelUnavailableError` (400 upstream).
- Undecodable audio → surfaced as a 422 by the service.
- No GPU → CPU (never a hard failure). Apple silicon → CPU (panns-inference has
  no MPS path).
- First run with no network → checkpoint/label download fails clearly; retries
  are safe (atomic `.part` downloads).

## Device selection
`cuda` if `torch.cuda.is_available()` else `cpu`. There is no `.cuda()` without a
CPU fallback and no assert/raise on a missing GPU.

## Verification
- Test files: `services/api/tests/test_tagging.py` (engine mocked at the module boundary — torch is never imported in tests)
- Required cases: labels/embedding shape, model-key validation, top-k selection.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [Taggings](taggings.md)
- [Labels index](labels-index.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
