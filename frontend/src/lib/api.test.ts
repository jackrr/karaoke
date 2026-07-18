import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createSession,
  listSessions,
  getSession,
  joinSession,
  leaveSession,
} from "./api";
import { __resetIdentityForTests, getClientId } from "./identity";

describe("api helpers", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    __resetIdentityForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    __resetIdentityForTests();
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
    it("posts name and display_name, returns session details", async () => {
      const res = {
        ok: true,
        json: vi.fn(() =>
          Promise.resolve({
            id: "abc",
            name: "test",
            passcode: "123456",
            host_client_id: "host-1",
            client_id: "host-1",
          }),
        ),
      };
      const fetchMock = vi.fn(() => Promise.resolve(res)) as any;
      vi.stubGlobal("fetch", fetchMock);

      const result = await createSession("test", "Alice");

      expect(result).toEqual({
        id: "abc",
        name: "test",
        passcode: "123456",
        host_client_id: "host-1",
        client_id: "host-1",
      });
      const [, init] = fetchMock.mock.calls[0];
      const body = JSON.parse(init.body);
      expect(body.name).toBe("test");
      expect(body.display_name).toBe("Alice");
      expect(typeof body.client_id).toBe("string");
      expect(body.client_id.length).toBeGreaterThan(0);
    });

    it("sends the browser's persisted client_id so an existing identity survives creating a session", async () => {
      const res = {
        ok: true,
        json: vi.fn(() =>
          Promise.resolve({
            id: "abc",
            name: "test",
            passcode: "123456",
            host_client_id: "existing-client",
            client_id: "existing-client",
          }),
        ),
      };
      const fetchMock = vi.fn(() => Promise.resolve(res)) as any;
      vi.stubGlobal("fetch", fetchMock);

      const existingId = getClientId();
      await createSession("test", "Alice");

      const [, init] = fetchMock.mock.calls[0];
      const body = JSON.parse(init.body);
      expect(body.client_id).toBe(existingId);
    });
  });

  describe("joinSession", () => {
    it("posts passcode, display_name, and client_id", async () => {
      const res = {
        ok: true,
        json: vi.fn(() =>
          Promise.resolve({
            id: "abc",
            name: "test",
            client_id: "guest-1",
            is_host: false,
          }),
        ),
      };
      const fetchMock = vi.fn(() => Promise.resolve(res)) as any;
      vi.stubGlobal("fetch", fetchMock);

      const result = await joinSession("123456", "Bob");

      expect(result).toEqual({
        id: "abc",
        name: "test",
        client_id: "guest-1",
        is_host: false,
      });
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/sessions/join");
      const body = JSON.parse(init.body);
      expect(body.passcode).toBe("123456");
      expect(body.display_name).toBe("Bob");
      expect(typeof body.client_id).toBe("string");
    });

    it("throws when the request fails", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
      );
      await expect(joinSession("000000", "Bob")).rejects.toThrow();
    });
  });

  describe("getSession", () => {
    it("returns null on 404", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
      );
      const result = await getSession("missing");
      expect(result).toBeNull();
    });

    it("returns session data including participants", async () => {
      const sessionData = {
        id: "abc",
        name: "test",
        created_at: "now",
        online: 1,
        passcode: "123456",
        host_client_id: "host-1",
        participants: [
          { client_id: "host-1", display_name: "Alice", is_host: true },
        ],
      };
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(sessionData),
          }),
        ),
      );
      const result = await getSession("abc");
      expect(result).toEqual(sessionData);
    });
  });

  describe("leaveSession", () => {
    it("posts the client_id", async () => {
      const fetchMock = vi.fn(() =>
        Promise.resolve({ ok: true, status: 204 }),
      ) as any;
      vi.stubGlobal("fetch", fetchMock);

      await leaveSession("abc");

      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/sessions/abc/leave");
      const body = JSON.parse(init.body);
      expect(typeof body.client_id).toBe("string");
    });
  });
});
