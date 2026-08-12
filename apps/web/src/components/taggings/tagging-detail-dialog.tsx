"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { getPreviewUrl } from "@/lib/api-client";
import { usePreviewUrl, useTaggingDetail } from "@/lib/queries";
import type { Tagging } from "@panns-audioset-tagging/shared";

interface TaggingDetailDialogProps {
  audioKey: string | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Small bar-chart of the first N embedding dimensions. */
function EmbeddingSparkline({ embedding }: { embedding: number[] }) {
  const slice = embedding.slice(0, 64);
  const max = Math.max(1e-6, ...slice.map((v) => Math.abs(v)));
  return (
    <div className="flex h-12 items-end gap-[2px]">
      {slice.map((v, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm bg-primary/70"
          style={{ height: `${Math.max(2, (Math.abs(v) / max) * 100)}%` }}
          title={`dim ${i}: ${v.toFixed(4)}`}
        />
      ))}
    </div>
  );
}

function TaggingDetailBody({ tagging }: { tagging: Tagging }) {
  const [rawLoading, setRawLoading] = useState(false);
  const audio = usePreviewUrl(tagging.audio_key, true);

  const openRawJson = async () => {
    setRawLoading(true);
    try {
      const { url } = await getPreviewUrl(tagging.tag_key);
      window.open(url, "_blank", "noopener,noreferrer");
    } finally {
      setRawLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Inline audio player (presigned URL) */}
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Source clip
        </p>
        {audio.data?.url ? (
          <audio controls src={audio.data.url} className="w-full" />
        ) : (
          <Skeleton className="h-10 w-full" />
        )}
        <p className="mt-1 font-mono text-xs text-muted-foreground break-all">
          {tagging.audio_key}
        </p>
      </div>

      <Separator />

      {/* Top-k labels as probability bars */}
      <div>
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Top {tagging.labels.length} AudioSet labels
        </p>
        <div className="space-y-2.5">
          {tagging.labels.map((label) => (
            <div key={label.label} className="space-y-1">
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="truncate">{label.label}</span>
                <span className="font-mono text-xs tabular-nums text-muted-foreground">
                  {(label.probability * 100).toFixed(1)}%
                </span>
              </div>
              <Progress value={label.probability * 100} className="h-1.5" />
            </div>
          ))}
        </div>
      </div>

      <Separator />

      {/* Embedding summary */}
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Embedding
        </p>
        <div className="mb-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <span>
            <span className="text-muted-foreground">dim </span>
            <span className="font-mono tabular-nums">{tagging.embedding_dim}</span>
          </span>
          <span>
            <span className="text-muted-foreground">L2 norm </span>
            <span className="font-mono tabular-nums">
              {tagging.embedding_l2_norm.toFixed(3)}
            </span>
          </span>
          <span>
            <span className="text-muted-foreground">model </span>
            <span className="font-mono">{tagging.model}</span>
          </span>
        </div>
        <EmbeddingSparkline embedding={tagging.embedding} />
        <p className="mt-1 text-xs text-muted-foreground">
          First 64 of {tagging.embedding_dim} dimensions.
        </p>
      </div>

      <Separator />

      {/* Source metadata + raw artifact link */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <span>
            <span className="text-muted-foreground">duration </span>
            <span className="font-mono tabular-nums">
              {tagging.source_metadata.duration_seconds !== null
                ? `${tagging.source_metadata.duration_seconds.toFixed(1)}s`
                : "—"}
            </span>
          </span>
          <span>
            <span className="text-muted-foreground">sample rate </span>
            <span className="font-mono tabular-nums">
              {tagging.source_metadata.sample_rate !== null
                ? `${(tagging.source_metadata.sample_rate / 1000).toFixed(1)} kHz`
                : "—"}
            </span>
          </span>
          <span>
            <span className="text-muted-foreground">channels </span>
            <span className="font-mono tabular-nums">
              {tagging.source_metadata.channels ?? "—"}
            </span>
          </span>
        </div>
        <Button variant="outline" size="sm" onClick={openRawJson} disabled={rawLoading}>
          <ExternalLink className="h-3.5 w-3.5" />
          {rawLoading ? "Opening…" : "Raw tag JSON"}
        </Button>
      </div>
    </div>
  );
}

export function TaggingDetailDialog({
  audioKey,
  open,
  onOpenChange,
}: TaggingDetailDialogProps) {
  const detail = useTaggingDetail(audioKey, open);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Tagging detail</DialogTitle>
          <DialogDescription>
            PANNs AudioSet labels and the 2048-dim embedding for this clip.
          </DialogDescription>
        </DialogHeader>
        {detail.isLoading && <Skeleton className="h-64 w-full" />}
        {detail.isError && (
          <ErrorState error={detail.error} onRetry={() => detail.refetch()} />
        )}
        {detail.data && <TaggingDetailBody tagging={detail.data} />}
      </DialogContent>
    </Dialog>
  );
}
