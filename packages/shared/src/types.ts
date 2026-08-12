export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when the audio extractor was skipped or failed (non-audio object, or a
   *  clip whose header could not be read). Core fields stay exact. */
  metadata_warning: string | null;
  // Audio-specific (read from the clip header via soundfile).
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- PANNs AudioSet tagging ------------------------------------------------

/** Finite, selector-backed fields (mirrored by the create/edit forms). */
export type ModelKey = "cnn14-32k" | "cnn14-16k";
export type TopK = 5 | 10 | 15 | 20;

export interface Label {
  label: string;
  probability: number;
}

export interface AudioMetadata {
  duration_seconds: number | null;
  sample_rate: number | null;
  channels: number | null;
}

/** List-view projection of a Tagging (no embedding vector). */
export interface TaggingSummary {
  audio_key: string;
  tag_key: string;
  model: string;
  top_k: number;
  labels: Label[];
  tagged_at: string;
  duration_seconds: number | null;
}

/** Full Tagging detail, including the 2048-dim embedding and its stats. */
export interface Tagging extends TaggingSummary {
  embedding: number[];
  embedding_dim: number;
  embedding_l2_norm: number;
  source_metadata: AudioMetadata;
}

export interface CreateTaggingRequest {
  audio_key: string;
  model: ModelKey;
  top_k: TopK;
}

export interface EditTaggingRequest {
  audio_key: string;
  model: ModelKey;
  top_k: TopK;
}

export interface RunTaggingRequest {
  audio_key: string;
}

export interface ManifestEntry {
  audio_key: string;
  tag_key: string;
  model: string;
  top_k: number;
  top_labels: Label[];
  tagged_at: string;
  duration_seconds: number | null;
}

export interface TopLabelCount {
  label: string;
  count: number;
}

export interface CorpusStats {
  clips_ingested: number;
  clips_tagged: number;
  pct_tagged: number;
  distinct_labels: number;
  top_labels: TopLabelCount[];
  recent_taggings: TaggingSummary[];
}

/** A clip under the sample-scoped audio/ prefix, with tag status. */
export interface LibraryClip {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
  tagged: boolean;
  tag_key: string | null;
  duration_seconds: number | null;
}
