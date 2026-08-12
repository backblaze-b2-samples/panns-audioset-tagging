"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type {
  CreateTaggingRequest,
  LibraryClip,
  ModelKey,
  TopK,
} from "@panns-audioset-tagging/shared";

// Finite-option fields use selectors, never free text (see the plan's Form UX
// conventions). top_k is kept as a string in the form and coerced on submit.
const MODEL_OPTIONS: { value: ModelKey; label: string }[] = [
  { value: "cnn14-32k", label: "Cnn14 (32 kHz)" },
  { value: "cnn14-16k", label: "Cnn14 (16 kHz)" },
];
const TOP_K_OPTIONS: TopK[] = [5, 10, 15, 20];

const schema = z.object({
  audio_key: z.string().min(1, "Pick a clip from the Library"),
  model: z.enum(["cnn14-32k", "cnn14-16k"]),
  top_k: z.enum(["5", "10", "15", "20"]),
});

type FormValues = z.infer<typeof schema>;

export interface TaggingFormProps {
  mode: "create" | "edit";
  /** Clips to choose from on the create form (ignored on edit). */
  clips?: LibraryClip[];
  defaultValues?: Partial<CreateTaggingRequest>;
  submitting?: boolean;
  onSubmit: (values: CreateTaggingRequest) => void;
}

export function TaggingForm({
  mode,
  clips = [],
  defaultValues,
  submitting = false,
  onSubmit,
}: TaggingFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      audio_key: defaultValues?.audio_key ?? "",
      model: defaultValues?.model ?? "cnn14-32k",
      top_k: String(defaultValues?.top_k ?? 10) as FormValues["top_k"],
    },
  });

  const handleSubmit = (values: FormValues) => {
    onSubmit({
      audio_key: values.audio_key,
      model: values.model,
      top_k: Number(values.top_k) as TopK,
    });
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(handleSubmit)}
        className="space-y-5"
        id="tagging-form"
      >
        <FormField
          control={form.control}
          name="audio_key"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Audio clip</FormLabel>
              {mode === "edit" ? (
                // The clip is the Tagging's identity — read-only on edit.
                <FormControl>
                  <Input value={field.value} readOnly className="font-mono text-xs" />
                </FormControl>
              ) : (
                <Select onValueChange={field.onChange} value={field.value}>
                  <FormControl>
                    <SelectTrigger>
                      <SelectValue placeholder="Pick a clip from the Library" />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {clips.map((clip) => (
                      <SelectItem key={clip.key} value={clip.key}>
                        {clip.filename}
                        {clip.tagged ? " · already tagged" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
              <FormDescription>
                {mode === "edit"
                  ? "The source clip cannot change — create a new tagging to tag a different clip."
                  : "Ingest clips on the Ingest page; pick the first available clip to start."}
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="model"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Model</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {MODEL_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>
                Cnn14 (32 kHz) — best general accuracy. Runs locally on CPU.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="top_k"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Top-k labels</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {TOP_K_OPTIONS.map((k) => (
                    <SelectItem key={k} value={String(k)}>
                      {k} labels
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FormDescription>10 labels is a good default.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="flex justify-end">
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Tagging…"
              : mode === "edit"
                ? "Save & re-tag"
                : "Run tagging"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
