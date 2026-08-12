import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("PANNs AudioSet Tagging");
    expect(APP_DESCRIPTION).toBe(
      "Tag audio collections with AudioSet labels + embeddings, stored on Backblaze B2"
    );
  });
});
