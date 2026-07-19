import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import YoutubeDownloadForm from "./YoutubeDownloadForm.svelte";
import type { Track } from "../api";
import { DuplicateTrackError } from "../api";

function makeTrack(overrides: Partial<Track> = {}): Track {
  return {
    id: "t1",
    session_id: "s1",
    source_url: "https://youtube.com/watch?v=xyz",
    youtube_video_id: "xyz",
    title: "A Song",
    status: "pending",
    error_message: null,
    audio_path: null,
    lyrics_path: null,
    lyrics_source: null,
    duration_seconds: null,
    requested_by_client_id: "c1",
    created_at: "now",
    updated_at: "now",
    ...overrides,
  };
}

describe("YoutubeDownloadForm", () => {
  it("renders the form and an empty track list", () => {
    render(YoutubeDownloadForm, {
      tracks: [],
      onSubmit: vi.fn(),
      onPlay: vi.fn(),
    });
    expect(screen.getByPlaceholderText("Paste a YouTube URL...")).toBeTruthy();
    expect(screen.getByRole("button", { name: /add track/i })).toBeTruthy();
  });

  it("renders tracks passed in as a prop with their status", () => {
    render(YoutubeDownloadForm, {
      tracks: [makeTrack({ status: "downloaded", title: "Song One" })],
      onSubmit: vi.fn(),
      onPlay: vi.fn(),
    });
    expect(screen.getByText("Song One")).toBeTruthy();
    expect(screen.getByText("Downloaded")).toBeTruthy();
  });

  it("shows the error message for a track in error status", () => {
    render(YoutubeDownloadForm, {
      tracks: [
        makeTrack({ status: "error", error_message: "Download failed" }),
      ],
      onSubmit: vi.fn(),
      onPlay: vi.fn(),
    });
    expect(screen.getByText("Download failed")).toBeTruthy();
  });

  it("disables the submit button while submitting, then re-enables it", async () => {
    let resolveSubmit: (track: Track) => void = () => {};
    const onSubmit = vi.fn(
      () =>
        new Promise<Track>((resolve) => {
          resolveSubmit = resolve;
        }),
    );
    render(YoutubeDownloadForm, { tracks: [], onSubmit, onPlay: vi.fn() });

    const input = screen.getByPlaceholderText(
      "Paste a YouTube URL...",
    ) as HTMLInputElement;
    const button = screen.getByRole("button", {
      name: /add track/i,
    }) as HTMLButtonElement;

    await fireEvent.input(input, {
      target: { value: "https://youtube.com/watch?v=xyz" },
    });
    await fireEvent.click(button);

    await waitFor(() => expect(button.disabled).toBe(true));

    resolveSubmit(makeTrack());
    await waitFor(() => expect(button.disabled).toBe(true)); // empty input keeps it disabled
  });

  it("shows a distinct message for a duplicate (409) submission", async () => {
    const existing = makeTrack();
    const onSubmit = vi.fn(() =>
      Promise.reject(new DuplicateTrackError(existing)),
    );
    render(YoutubeDownloadForm, { tracks: [], onSubmit, onPlay: vi.fn() });

    const input = screen.getByPlaceholderText(
      "Paste a YouTube URL...",
    ) as HTMLInputElement;
    const button = screen.getByRole("button", { name: /add track/i });

    await fireEvent.input(input, {
      target: { value: "https://youtube.com/watch?v=xyz" },
    });
    await fireEvent.click(button);

    await waitFor(() =>
      expect(screen.getByText(/already been added/i)).toBeTruthy(),
    );
  });

  it("shows a generic error message on other submission failures", async () => {
    const onSubmit = vi.fn(() => Promise.reject(new Error("boom")));
    render(YoutubeDownloadForm, { tracks: [], onSubmit, onPlay: vi.fn() });

    const input = screen.getByPlaceholderText(
      "Paste a YouTube URL...",
    ) as HTMLInputElement;
    const button = screen.getByRole("button", { name: /add track/i });

    await fireEvent.input(input, {
      target: { value: "https://youtube.com/watch?v=xyz" },
    });
    await fireEvent.click(button);

    await waitFor(() =>
      expect(screen.getByText(/failed to add track/i)).toBeTruthy(),
    );
  });
});
