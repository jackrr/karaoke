import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  createSession,
  listSessions,
  getSession,
  joinSession,
  leaveSession,
  submitYoutubeUrl,
  listTracks,
  DuplicateTrackError,
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

  describe("submitYoutubeUrl", () => {
    it("posts url and client_id, returns the created track", async () => {
      const track = {
        id: "t1",
        session_id: "abc",
        source_url: "https://youtube.com/watch?v=xyz",
        youtube_video_id: "xyz",
        title: null,
        status: "pending",
        error_message: null,
        audio_path: null,
        lyrics_path: null,
        lyrics_source: null,
        duration_seconds: null,
        requested_by_client_id: "client-1",
        created_at: "now",
        updated_at: "now",
      };
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 202,
          json: () => Promise.resolve(track),
        }),
      ) as any;
      vi.stubGlobal("fetch", fetchMock);

      const result = await submitYoutubeUrl(
        "abc",
        "https://youtube.com/watch?v=xyz",
      );

      expect(result).toEqual(track);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toBe("/sessions/abc/tracks");
      const body = JSON.parse(init.body);
      expect(body.url).toBe("https://youtube.com/watch?v=xyz");
      expect(typeof body.client_id).toBe("string");
    });

    it("throws DuplicateTrackError with the existing track on 409", async () => {
      const existing = {
        id: "t1",
        session_id: "abc",
        source_url: "https://youtube.com/watch?v=xyz",
        youtube_video_id: "xyz",
        title: "Existing",
        status: "downloaded",
        error_message: null,
        audio_path: "/path",
        lyrics_path: null,
        lyrics_source: "none",
        duration_seconds: 10,
        requested_by_client_id: "client-1",
        created_at: "now",
        updated_at: "now",
      };
      vi.stubGlobal(
        "fetch",
        vi.fn(() =>
          Promise.resolve({
            ok: false,
            status: 409,
            json: () => Promise.resolve(existing),
          }),
        ),
      );

      await expect(
        submitYoutubeUrl("abc", "https://youtube.com/watch?v=xyz"),
      ).rejects.toThrow(DuplicateTrackError);
    });

    it("throws a generic error on other failures", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve({ ok: false, status: 422 })),
      );

      await expect(submitYoutubeUrl("abc", "not-a-url")).rejects.toThrow();
    });
  });

  describe("listTracks", () => {
    it("returns tracks from fetch", async () => {
      const tracks = [
        {
          id: "t1",
          session_id: "abc",
          source_url: "https://youtube.com/watch?v=xyz",
          youtube_video_id: "xyz",
          title: "A Song",
          status: "downloaded",
          error_message: null,
          audio_path: "/path",
          lyrics_path: null,
          lyrics_source: "none",
          duration_seconds: 10,
          requested_by_client_id: "client-1",
          created_at: "now",
          updated_at: "now",
        },
      ];
      const fetchMock = vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ tracks }),
        }),
      ) as any;
      vi.stubGlobal("fetch", fetchMock);

      const result = await listTracks("abc");

      expect(result).toEqual(tracks);
      expect(fetchMock).toHaveBeenCalledWith("/sessions/abc/tracks");
    });

    it("throws when the request fails", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn(() => Promise.resolve({ ok: false, status: 500 })),
      );
      await expect(listTracks("abc")).rejects.toThrow();
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
