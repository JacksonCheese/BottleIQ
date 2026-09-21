import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useResource } from "@/lib/use-resource";
afterEach(() => vi.unstubAllGlobals());
it("loads API data after an initial loading state", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ total: 7 }) }),
  );
  const { result } = renderHook(() =>
    useResource<{ total: number }>("/dashboard"),
  );
  expect(result.current.data).toBeUndefined();
  await waitFor(() => expect(result.current.data?.total).toBe(7));
});
it("surfaces backend validation errors", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "Upload inventory first" }),
    }),
  );
  const { result } = renderHook(() => useResource("/dashboard"));
  await waitFor(() =>
    expect(result.current.error).toBe("Upload inventory first"),
  );
});
it("never exposes data from a previous store while switching", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ["store-a"] })
    .mockImplementationOnce(() => new Promise(() => {}));
  vi.stubGlobal("fetch", fetch);
  const { result, rerender } = renderHook(
    ({ path }) => useResource<string[]>(path),
    { initialProps: { path: "/inventory?store_id=a" } },
  );
  await waitFor(() => expect(result.current.data).toEqual(["store-a"]));
  rerender({ path: "/inventory?store_id=b" });
  expect(result.current.data).toBeUndefined();
});
