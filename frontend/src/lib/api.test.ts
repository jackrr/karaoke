import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createSession, listSessions, getSession } from "./api";

describe("api helpers", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("listSessions", () => {
    it("returns sessions from fetch", async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: vi.fn(() => Promise.resolve({ sessions: [] })),
        }),
      ) as any;
      vi.stubGlobal("fetch", fetchMock);
      await listSessions();
      expect(fetchMock).toHaveBeenCalledWith("/sessions");
    });
  });

  describe("createSession", () => {
    it("posts name and returns id/name", async () => {
      const res = {
        ok: true,
        json: vi.fn(() => Promise.resolve({ id: "abc", name: "test" })),
      };
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve(res)),
      );
      const result = await createSession("test");
      expect(result).toEqual({ id: "abc", name: "test" });
    });
  });
});
