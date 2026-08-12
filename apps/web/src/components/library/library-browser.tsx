"use client";

import Link from "next/link";
import { AudioLines, Tag, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCreateTagging, useLibrary } from "@/lib/queries";
import type { LibraryClip } from "@panns-audioset-tagging/shared";

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function LibraryBrowser() {
  const library = useLibrary();
  const createMutation = useCreateTagging();

  const tagClip = (clip: LibraryClip) => {
    createMutation.mutate(
      { audio_key: clip.key, model: "cnn14-32k", top_k: 10 },
      {
        onSuccess: () =>
          toast.success("Clip tagged", { description: clip.filename }),
        onError: (e) => toast.error("Tagging failed", { description: e.message }),
      }
    );
  };

  return (
    <Card className="overflow-hidden">
      {library.isLoading ? (
        <div className="space-y-2 p-5">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-8 w-full" />
        </div>
      ) : library.isError ? (
        <ErrorState
          error={library.error}
          onRetry={() => library.refetch()}
          className="py-10"
        />
      ) : library.data && library.data.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Clip</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {library.data.map((clip) => (
              <TableRow key={clip.key}>
                <TableCell className="max-w-[18rem] truncate font-medium">
                  {clip.filename}
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {formatDuration(clip.duration_seconds)}
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {clip.size_human}
                </TableCell>
                <TableCell>
                  {clip.tagged ? (
                    <Badge variant="secondary" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Tagged
                    </Badge>
                  ) : (
                    <Badge variant="outline">Untagged</Badge>
                  )}
                </TableCell>
                <TableCell className="text-right">
                  {clip.tagged ? (
                    <Button asChild variant="ghost" size="sm">
                      <Link href="/taggings">View taggings</Link>
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      onClick={() => tagClip(clip)}
                      disabled={
                        createMutation.isPending &&
                        createMutation.variables?.audio_key === clip.key
                      }
                    >
                      <Tag className="h-3.5 w-3.5" />
                      Tag
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState
          icon={AudioLines}
          title="No clips ingested yet"
          description="Upload WAV/FLAC/MP3 clips on the Ingest page. They land under the audio/ prefix and appear here."
          action={
            <Button asChild size="sm">
              <Link href="/upload">Go to Ingest</Link>
            </Button>
          }
        />
      )}
    </Card>
  );
}
