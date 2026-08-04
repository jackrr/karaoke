import { describe, it, expect, vi, afterEach } from "vitest";
import { render, waitFor } from "@testing-library/svelte";
import TrackPlayer from "./TrackPlayer.svelte";
import * as api from "../api";
import type { Track } from "../api";

function makeTrack(overrides: Partial<Track> = {}): Track {
  return {
    id: "t1",
    session_id: "s1",
    source_url: "https://youtube.com/watch?v=xyz",
    youtube_video_id: "xyz",
    title: "A Song",
    artist: "An Artist",
    status: "downloaded",
    error_message: null,
    audio_path: "/path/audio.m4a",
    lyrics_path: "/path/lyrics.lrc",
    lyrics_source: "captions",
    duration_seconds: 42,
    requested_by_client_id: "c1",
    requested_by_display_name: null,
    position: 0,
    created_at: "now",
    updated_at: "now",
    ...overrides,
  };
}

describe("TrackPlayer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hides the native audio controls and renders PlaybackControls instead", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );

    const { container, getByRole } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack(),
      onStop: vi.fn(),
    });

    const audio = container.querySelector("audio");
    expect(audio).toBeTruthy();
    expect(audio?.hasAttribute("controls")).toBe(false);
    expect(getComputedStyle(audio!).display).toBe("none");

    expect(getByRole("button", { name: "Play" })).toBeTruthy();
    expect(getByRole("button", { name: "Stop" })).toBeTruthy();
  });

  it("announces the title and artist on track change, then hides after a few seconds", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );
    vi.useFakeTimers();

    const { getByText, queryByText } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack({ title: "A Song", artist: "An Artist" }),
      onStop: vi.fn(),
    });

    expect(getByText("A Song")).toBeTruthy();
    expect(getByText("An Artist")).toBeTruthy();

    await vi.advanceTimersByTimeAsync(4000);

    expect(queryByText("A Song")).toBeNull();
    expect(queryByText("An Artist")).toBeNull();

    vi.useRealTimers();
  });

  it("re-announces on transition to a new track", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );

    const trackA = makeTrack({ id: "t1", title: "Song A", artist: "Artist A" });
    const trackB = makeTrack({ id: "t2", title: "Song B", artist: "Artist B" });

    const { getByText, rerender } = render(TrackPlayer, {
      sessionId: "s1",
      track: trackA,
      onStop: vi.fn(),
    });

    expect(getByText("Song A")).toBeTruthy();

    await rerender({ sessionId: "s1", track: trackB, onStop: vi.fn() });

    await waitFor(() => expect(getByText("Song B")).toBeTruthy());
    expect(getByText("Artist B")).toBeTruthy();
  });

  it("calls updatePlaybackState with the track id when playback state changes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );
    const updateSpy = vi
      .spyOn(api, "updatePlaybackState")
      .mockResolvedValue({ track_id: "t1", is_playing: true });

    const { container } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack({ id: "t1" }),
      onStop: vi.fn(),
    });

    const audio = container.querySelector("audio")!;
    // Dispatch the audio element's own 'play' event directly rather than
    // calling audio.play() (unimplemented in jsdom), matching how
    // PlaybackControls listens for state changes regardless of cause.
    Object.defineProperty(audio, "paused", {
      value: false,
      configurable: true,
    });
    audio.dispatchEvent(new Event("play"));

    await waitFor(() =>
      expect(updateSpy).toHaveBeenCalledWith("s1", "t1", true),
    );
  });

  it("shows a message when lyrics are unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404 })),
    );

    const { getByText } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack(),
      onStop: vi.fn(),
    });

    await waitFor(() => expect(getByText(/no lyrics available/i)).toBeTruthy());
  });

  it("renders the current lyric line and previews the next once lyrics resolve", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          status: 200,
          text: () => Promise.resolve("[00:00.00]Hello\n[00:03.00]World"),
        }),
      ),
    );

    const { getByText } = render(TrackPlayer, {
      sessionId: "s1",
      track: makeTrack(),
      onStop: vi.fn(),
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
          text: () => Promise.resolve("[00:00.00]Hello\n[00:03.00]World"),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve("[00:00.00]Goodbye\n[00:03.00]Moon"),
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const trackA = makeTrack({ id: "t1" });
    const trackB = makeTrack({ id: "t2" });

    const { getByText, queryByText, rerender } = render(TrackPlayer, {
      sessionId: "s1",
      track: trackA,
      onStop: vi.fn(),
    });

    await waitFor(() => expect(getByText("Hello")).toBeTruthy());

    await rerender({ sessionId: "s1", track: trackB, onStop: vi.fn() });

    await waitFor(() => expect(getByText("Goodbye")).toBeTruthy());
    expect(queryByText("Hello")).toBeNull();
    expect(queryByText("World")).toBeNull();
  });
});
