import Link from "next/link";
import { AudioLines } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CorpusDashboard } from "@/components/dashboard/corpus-dashboard";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Tagged coverage and the top-label distribution across your audio
            corpus on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <AudioLines className="h-3.5 w-3.5" />
            Ingest clips
          </Link>
        </Button>
      </div>
      <CorpusDashboard />
    </div>
  );
}
