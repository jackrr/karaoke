import { describe, it, expect, vi, afterEach } from "vitest";
import { render, waitFor } from "@testing-library/svelte";
import TrackPlayer from "./TrackPlayer.svelte";
import type { Track } from "../api";

function makeTrack(overrides: Partial<Track> = {}): Track {
  return {
    id: "t1",
    session_id: "s1",
    source_url: "https://youtube.com/watch?v=xyz",
    youtube_video_id: "xyz",
    title: "A Song",
    status: "downloaded",
    error_message: null,
    audio_path: "/path/audio.m4a",
    lyrics_path: "/path/lyrics.lrc",
    lyrics_source: "captions",
    duration_seconds: 42,
    requested_by_client_id: "c1",
    created_at: "now",
    updated_at: "now",
    ...overrides,
  };
}

describe("TrackPlayer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a message when lyrics are unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );

    const { getByText } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack(),
    });

    await waitFor(() => expect(getByText(/no lyrics available/i)).toBeTruthy());
  });

  it("renders lyrics once they resolve successfully", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve("[00:01.00]Hello\n[00:03.00]World"),
        }),
      ),
    );

    const { getByText } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack(),
    });

    await waitFor(() => expect(getByText("Hello")).toBeTruthy());
    expect(getByText("World")).toBeTruthy();
  });

  it("refetches and updates lyrics when the track changes, without showing stale content", async () => {
    const fetchMock = vi.fn((url: string) => {
      if (url.includes("/tracks/t1/")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve("[00:01.00]Hello\n[00:03.00]World"),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve("[00:01.00]Goodbye\n[00:03.00]Moon"),
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const trackA = makeTrack({ id: "t1" });
    const trackB = makeTrack({ id: "t2" });

    const { getByText, queryByText, rerender } = render(TrackPlayer, {
      sessionId: "s1",
      track: trackA,
    });

    await waitFor(() => expect(getByText("Hello")).toBeTruthy());
    expect(getByText("World")).toBeTruthy();

    await rerender({ sessionId: "s1", track: trackB });

    await waitFor(() => expect(getByText("Goodbye")).toBeTruthy());
    expect(getByText("Moon")).toBeTruthy();
    expect(queryByText("Hello")).toBeNull();
    expect(queryByText("World")).toBeNull();
  });
});
