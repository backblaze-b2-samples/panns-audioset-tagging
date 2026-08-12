<!-- last_verified: 2026-08-12 -->
# Feature: labels_index.jsonl manifest

## Purpose
A single, flat dataset index at the bucket root that downstream training and
search jobs read over the S3 API — one JSON line per tagged clip. It is derived
state, rebuilt from `tags/` after every write, so it is always consistent with
the per-clip tag artifacts.

## Used By
- API: `GET /taggings/manifest` (and the Library / Dashboard read it directly)
- Service: `services/api/app/service/tagging.py` (`_rebuild_manifest`, `get_manifest`)

## Core Functions
- `_rebuild_manifest()` — lists every `tags/…json`, reads each, and overwrites
  `labels_index.jsonl` (idempotent; no read-modify-write race).
- `get_manifest()` — parses the JSONL back into `ManifestEntry[]`.

## Canonical Files
- Manifest logic: `services/api/app/service/tagging.py`

## Format
One JSON object per line:

```json
{"audio_key": "audio/dog.wav", "tag_key": "tags/audio/dog.wav.json",
 "model": "cnn14-32k", "top_k": 10,
 "top_labels": [{"label": "Dog", "probability": 0.92}, {"label": "Animal", "probability": 0.81}],
 "tagged_at": "2026-08-12T10:00:00+00:00", "duration_seconds": 3.2}
```

`top_labels` carries the top-k labels *with* probabilities so a job can consume
the index without opening every per-clip tag JSON.

## Flow
- On any create / edit / run / delete, the service lists `tags/`, reads each tag
  JSON, and rewrites `labels_index.jsonl` from scratch.
- Consumers (a training job, a search indexer, the Dashboard, the Library) read
  the single manifest object rather than scanning `tags/`.

## How a training job consumes it
```python
import json, boto3
s3 = boto3.client("s3", endpoint_url=f"https://s3.{region}.backblazeb2.com")
body = s3.get_object(Bucket=bucket, Key="labels_index.jsonl")["Body"].read()
for line in body.decode().splitlines():
    row = json.loads(line)
    # row["audio_key"], row["top_labels"], row["tag_key"] (full embedding in the tag JSON)
```

## Edge Cases
- Manifest missing → treated as empty (no taggings yet), never an error.
- An unreadable/corrupt tag object is skipped during rebuild, not fatal.
- Deleting the last tagging leaves an empty manifest object.

## Verification
- Test files: `services/api/tests/test_tagging.py`
- Required cases: manifest has one entry after a create; delete drops the line.
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Pass criteria: focused tests and `pnpm verify` green.

## Related Docs
- [Taggings](taggings.md)
- [Audio tagging engine](audio-tagging.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
