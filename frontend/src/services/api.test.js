import { describe, expect, it } from "vitest";

import { getFrameUrl } from "./api";

describe("getFrameUrl", () => {
  it("includes the slot, source id, and cache buster in the preview URL", () => {
    const url = getFrameUrl(123456, 2, 55);
    const parsed = new URL(url);

    expect(parsed.pathname).toBe("/api/inference/frame/");
    expect(parsed.searchParams.get("slot")).toBe("2");
    expect(parsed.searchParams.get("source_id")).toBe("55");
    expect(parsed.searchParams.get("t")).toBe("123456");
  });
});
