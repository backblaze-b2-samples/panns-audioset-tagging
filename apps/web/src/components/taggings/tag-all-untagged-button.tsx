"use client";

import { useState } from "react";
import { Loader2, Tags } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useCreateTagging, useLibrary } from "@/lib/queries";

interface TagAllUntaggedButtonProps {
  variant?: React.ComponentProps<typeof Button>["variant"];
  size?: React.ComponentProps<typeof Button>["size"];
}

/**
 * One-click bulk tagging for the whole untagged corpus — the sample's headline
 * "tag a large collection" path. It reuses the existing per-clip tagging
 * endpoint (via `useCreateTagging`) over the snapshot of untagged clips taken at
 * click time, so re-listing the Library mid-run never grows or shrinks the batch
 * under us. Self-hides when there is nothing untagged left to tag.
 */
export function TagAllUntaggedButton({
  variant = "default",
  size = "sm",
}: TagAllUntaggedButtonProps) {
  const library = useLibrary();
  const createMutation = useCreateTagging();
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(
    null,
  );

  const running = progress !== null;
  const untaggedCount = (library.data ?? []).filter((c) => !c.tagged).length;

  // Nothing to do and not mid-run — don't clutter the toolbar.
  if (!running && untaggedCount === 0) return null;

  const runAll = async () => {
    const targets = (library.data ?? []).filter((c) => !c.tagged);
    if (targets.length === 0) return;

    setProgress({ done: 0, total: targets.length });
    let ok = 0;
    let failed = 0;
    for (let i = 0; i < targets.length; i++) {
      try {
        await createMutation.mutateAsync({
          audio_key: targets[i].key,
          model: "cnn14-32k",
          top_k: 10,
        });
        ok += 1;
      } catch {
        failed += 1;
      }
      setProgress({ done: i + 1, total: targets.length });
    }
    setProgress(null);

    if (failed === 0) {
      toast.success(`Tagged ${ok} clip${ok === 1 ? "" : "s"}`);
    } else {
      toast.error(`Tagged ${ok}, ${failed} failed`, {
        description: "Some clips could not be tagged — retry them individually.",
      });
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      onClick={runAll}
      disabled={running}
      aria-live="polite"
    >
      {running ? (
        <>
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          Tagging {progress.done}/{progress.total}…
        </>
      ) : (
        <>
          <Tags className="h-3.5 w-3.5" aria-hidden="true" />
          Tag all untagged ({untaggedCount})
        </>
      )}
    </Button>
  );
}
