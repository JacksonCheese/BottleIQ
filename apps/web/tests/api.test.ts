import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

afterEach(() => vi.unstubAllGlobals());

it("gives a useful message when the API cannot be reached", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
  );
  await expect(api("/dashboard")).rejects.toThrow(
    "Cannot reach BottleIQ. Check your connection and try again.",
  );
});

it("includes the request code for a server error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Please retry.", request_id: "pilot-123" }),
        {
          status: 500,
          headers: { "Content-Type": "application/json" },
        },
      ),
    ),
  );
  await expect(api("/dashboard")).rejects.toThrow("report code pilot-123");
});
