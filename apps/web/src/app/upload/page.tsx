import { UploadForm } from "@/components/upload/upload-form";

export default function IngestPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Ingest</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload audio clips (WAV / FLAC / MP3) straight to Backblaze B2 under the{" "}
          <code>audio/</code> prefix. Ingested clips show up in the Library,
          ready to tag with PANNs. Up to 100 MB per file.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
