"use client";

import { useState } from "react";
import { Plus, Eye, Pencil, RefreshCw, Trash2, Tags } from "lucide-react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  useCreateTagging,
  useDeleteTagging,
  useEditTagging,
  useLibrary,
  useRunTagging,
  useTaggings,
} from "@/lib/queries";
import type {
  CreateTaggingRequest,
  TaggingSummary,
} from "@panns-audioset-tagging/shared";
import { TaggingForm } from "./tagging-form";
import { TaggingDetailDialog } from "./tagging-detail-dialog";
import { TagAllUntaggedButton } from "./tag-all-untagged-button";

function filenameOf(key: string): string {
  return key.split("/").pop() || key;
}

export function TaggingsWorkspace() {
  const taggings = useTaggings();
  const library = useLibrary();
  const createMutation = useCreateTagging();
  const editMutation = useEditTagging();
  const runMutation = useRunTagging();
  const deleteMutation = useDeleteTagging();

  const [newOpen, setNewOpen] = useState(false);
  const [editRow, setEditRow] = useState<TaggingSummary | null>(null);
  const [detailKey, setDetailKey] = useState<string | undefined>();
  const [deleteRow, setDeleteRow] = useState<TaggingSummary | null>(null);

  const handleCreate = (values: CreateTaggingRequest) => {
    createMutation.mutate(values, {
      onSuccess: () => {
        toast.success("Clip tagged", {
          description: `${filenameOf(values.audio_key)} · ${values.model}`,
        });
        setNewOpen(false);
      },
      onError: (e) => toast.error("Tagging failed", { description: e.message }),
    });
  };

  const handleEdit = (values: CreateTaggingRequest) => {
    editMutation.mutate(values, {
      onSuccess: () => {
        toast.success("Tagging updated", {
          description: filenameOf(values.audio_key),
        });
        setEditRow(null);
      },
      onError: (e) => toast.error("Update failed", { description: e.message }),
    });
  };

  const handleRun = (row: TaggingSummary) => {
    runMutation.mutate(row.audio_key, {
      onSuccess: () =>
        toast.success("Re-tagged", { description: filenameOf(row.audio_key) }),
      onError: (e) => toast.error("Re-tag failed", { description: e.message }),
    });
  };

  const confirmDelete = () => {
    if (!deleteRow) return;
    const row = deleteRow;
    deleteMutation.mutate(row.audio_key, {
      onSuccess: () =>
        toast.success("Tagging deleted", {
          description: filenameOf(row.audio_key),
        }),
      onError: (e) => toast.error("Delete failed", { description: e.message }),
    });
    setDeleteRow(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-end gap-2">
        <TagAllUntaggedButton size="sm" variant="outline" />
        <Button size="sm" onClick={() => setNewOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          New tagging
        </Button>
      </div>

      <Card className="overflow-hidden">
        {taggings.isLoading ? (
          <div className="space-y-2 p-5">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        ) : taggings.isError ? (
          <ErrorState
            error={taggings.error}
            onRetry={() => taggings.refetch()}
            className="py-10"
          />
        ) : taggings.data && taggings.data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Clip</TableHead>
                <TableHead>Model</TableHead>
                <TableHead className="text-center">Top-k</TableHead>
                <TableHead>Top label</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {taggings.data.map((row) => (
                <TableRow key={row.audio_key}>
                  <TableCell className="max-w-[16rem] truncate font-medium">
                    {filenameOf(row.audio_key)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono">
                      {row.model}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center tabular-nums">
                    {row.top_k}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {row.labels[0]
                      ? `${row.labels[0].label} (${(row.labels[0].probability * 100).toFixed(0)}%)`
                      : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        title="View"
                        onClick={() => setDetailKey(row.audio_key)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Edit"
                        onClick={() => setEditRow(row)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Re-tag"
                        disabled={
                          runMutation.isPending &&
                          runMutation.variables === row.audio_key
                        }
                        onClick={() => handleRun(row)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        title="Delete"
                        onClick={() => setDeleteRow(row)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <EmptyState
            icon={Tags}
            title="No taggings yet"
            description="Tag an ingested clip to produce AudioSet labels and an embedding, stored in B2 under tags/."
            action={
              <Button size="sm" onClick={() => setNewOpen(true)}>
                <Plus className="h-3.5 w-3.5" />
                New tagging
              </Button>
            }
          />
        )}
      </Card>

      {/* Create */}
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New tagging</DialogTitle>
            <DialogDescription>
              Run PANNs over an ingested clip. Inference is local — the first run
              downloads the ~300 MB checkpoint to ~/panns_data.
            </DialogDescription>
          </DialogHeader>
          <TaggingForm
            mode="create"
            clips={library.data ?? []}
            submitting={createMutation.isPending}
            onSubmit={handleCreate}
          />
        </DialogContent>
      </Dialog>

      {/* Edit */}
      <Dialog open={!!editRow} onOpenChange={(o) => !o && setEditRow(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit tagging</DialogTitle>
            <DialogDescription>
              Change the model or top-k and re-run. The source clip is fixed.
            </DialogDescription>
          </DialogHeader>
          {editRow && (
            <TaggingForm
              mode="edit"
              defaultValues={{
                audio_key: editRow.audio_key,
                model: editRow.model as CreateTaggingRequest["model"],
                top_k: editRow.top_k as CreateTaggingRequest["top_k"],
              }}
              submitting={editMutation.isPending}
              onSubmit={handleEdit}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Detail */}
      <TaggingDetailDialog
        audioKey={detailKey}
        open={!!detailKey}
        onOpenChange={(o) => !o && setDetailKey(undefined)}
      />

      {/* Delete */}
      <AlertDialog
        open={!!deleteRow}
        onOpenChange={(o) => !o && setDeleteRow(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this tagging?</AlertDialogTitle>
            <AlertDialogDescription>
              This removes the tag JSON and its manifest line. The source audio
              clip is kept. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
