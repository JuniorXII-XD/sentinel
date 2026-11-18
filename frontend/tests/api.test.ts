import { afterEach, describe, expect, it, vi } from "vitest";
import { api, setCsrf } from "../src/api";
afterEach(() => {
  vi.unstubAllGlobals();
  setCsrf("");
});
describe("authenticated API client", () => {
  it("uses same-origin cookies and CSRF headers without persistent browser tokens", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetcher);
    const storage = vi.spyOn(Storage.prototype, "setItem");
    setCsrf("test-csrf");
    await api("/alerts/1", { method: "PATCH", body: "{}" });
    expect(fetcher.mock.calls[0][1].credentials).toBe("same-origin");
    expect(fetcher.mock.calls[0][1].headers["X-CSRF-Token"]).toBe("test-csrf");
    expect(storage).not.toHaveBeenCalled();
  });
  it("signals expiry when a protected request loses its session", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":"Authentication required"}', { status: 401 }),
        ),
    );
    const listener = vi.fn();
    window.addEventListener("session-expired", listener);
    await expect(api("/events")).rejects.toThrow("Authentication required");
    expect(listener).toHaveBeenCalledOnce();
    window.removeEventListener("session-expired", listener);
  });
  it("surfaces validation failures and does not return error data as success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":"CSRF validation failed"}', { status: 403 }),
        ),
    );
    await expect(api("/auth/logout", { method: "POST" })).rejects.toThrow(
      "CSRF validation failed",
    );
  });
  it("returns downloadable report bytes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("CSV report", { status: 200 })),
    );
    const result = await api<Blob>("/reports/export?format=csv", {
      method: "POST",
    });
    expect(result.size).toBe(10);
  });
});
