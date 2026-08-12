import Link from "next/link";
import { AudioLines } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LibraryBrowser } from "@/components/library/library-browser";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Library</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
            Your ingested audio corpus (the <code>audio/</code> prefix in B2),
            with tag status per clip. Use the full-bucket Explorer to see every
            object, including tag JSON and the manifest.
          </p>
        </div>
        <Button asChild size="sm" className="h-8 shrink-0">
          <Link href="/upload">
            <AudioLines aria-hidden="true" className="h-3.5 w-3.5" />
            Ingest clips
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryBrowser />
      </div>
    </div>
  );
}
