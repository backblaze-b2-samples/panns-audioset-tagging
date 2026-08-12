import { TaggingsWorkspace } from "@/components/taggings/taggings-workspace";

export default function TaggingsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Taggings</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Run PANNs over ingested clips to produce 527-class AudioSet labels and
          a 2048-dim embedding. Every tag JSON and the labels_index.jsonl
          manifest are stored in Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <TaggingsWorkspace />
      </div>
    </div>
  );
}
