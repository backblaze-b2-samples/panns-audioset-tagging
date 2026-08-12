"use client";

import Link from "next/link";
import { AudioLines, Tags, Percent, ListMusic } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { useCorpusStats } from "@/lib/queries";
import type { CorpusStats } from "@panns-audioset-tagging/shared";

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  icon: LucideIcon;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <Icon className="h-4.5 w-4.5" />
        </div>
      </CardContent>
    </Card>
  );
}

function TopLabels({ stats }: { stats: CorpusStats }) {
  const max = Math.max(1, ...stats.top_labels.map((l) => l.count));
  return (
    <Card>
      <CardHeader className="border-b border-border px-5 py-4">
        <CardTitle className="card-title">Top labels</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {stats.top_labels.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No labels yet — tag a clip to populate the distribution.
          </p>
        ) : (
          <div className="space-y-2.5">
            {stats.top_labels.map((entry) => (
              <div key={entry.label} className="space-y-1">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="truncate">{entry.label}</span>
                  <span className="font-mono text-xs tabular-nums text-muted-foreground">
                    {entry.count}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${(entry.count / max) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecentTaggings({ stats }: { stats: CorpusStats }) {
  return (
    <Card>
      <CardHeader className="border-b border-border px-5 py-4">
        <CardTitle className="card-title">Recent taggings</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {stats.recent_taggings.length === 0 ? (
          <p className="text-sm text-muted-foreground">No taggings yet.</p>
        ) : (
          <ul className="divide-y divide-border">
            {stats.recent_taggings.map((row) => (
              <li
                key={row.audio_key}
                className="flex items-center justify-between gap-3 py-2.5 text-sm first:pt-0 last:pb-0"
              >
                <span className="min-w-0 truncate">
                  {row.audio_key.split("/").pop()}
                </span>
                <span className="shrink-0 text-muted-foreground">
                  {row.labels[0]?.label ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function CorpusDashboard() {
  const { data: stats, isLoading, isError, error, refetch } = useCorpusStats();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full" />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (!stats) return null;

  if (stats.clips_ingested === 0) {
    return (
      <EmptyState
        icon={AudioLines}
        title="No audio ingested yet"
        description="Upload clips on the Ingest page to start building your tagged corpus."
        action={
          <Button asChild size="sm">
            <Link href="/upload">Go to Ingest</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Clips ingested" value={stats.clips_ingested} icon={AudioLines} />
        <StatCard label="Clips tagged" value={stats.clips_tagged} icon={Tags} />
        <StatCard label="Tagged" value={`${stats.pct_tagged}%`} icon={Percent} />
        <StatCard label="Distinct labels" value={stats.distinct_labels} icon={ListMusic} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <TopLabels stats={stats} />
        <RecentTaggings stats={stats} />
      </div>
    </div>
  );
}
