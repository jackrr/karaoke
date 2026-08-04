import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/svelte";
import QueueList from "./QueueList.svelte";
import type { Track } from "../api";

function makeTrack(overrides: Partial<Track> = {}): Track {
  return {
    id: "t1",
    session_id: "s1",
    source_url: "https://youtube.com/watch?v=xyz",
    youtube_video_id: "xyz",
    title: "A Song",
    artist: "An Artist",
    status: "pending",
    error_message: null,
    audio_path: null,
    lyrics_path: null,
    lyrics_source: null,
    duration_seconds: null,
    requested_by_client_id: "c1",
    requested_by_display_name: null,
    position: 0,
    created_at: "now",
    updated_at: "now",
    ...overrides,
  };
}

describe("QueueList", () => {
  it("does not clobber a newer broadcast update when its own reorder rejects", async () => {
    const t1 = makeTrack({ id: "t1", title: "Song One" });
    const t2 = makeTrack({ id: "t2", title: "Song Two" });
    const t3 = makeTrack({ id: "t3", title: "Song Three" });

    let rejectOnReorder: (err: Error) => void;
    const onReorder = vi.fn(
      () =>
        new Promise<void>((_resolve, reject) => {
          rejectOnReorder = reject;
        }),
    );

    const { container, rerender } = render(QueueList, {
      tracks: [t1, t2],
      participants: [],
      onReorder,
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    // Start a reorder (t1, t2 -> t2, t1); onReorder's promise stays pending,
    // simulating an in-flight PUT to the backend.
    const list = container.querySelector("ul.tracks") as HTMLElement;
    const finalizeEvent = new CustomEvent("finalize", {
      detail: {
        items: [t2, t1],
        info: { trigger: "test", id: "t2", source: "test" },
      },
    });
    list.dispatchEvent(finalizeEvent);

    await waitFor(() => expect(onReorder).toHaveBeenCalled());

    // While the PUT is still in flight, a queue_reordered broadcast from
    // another member's concurrent reorder arrives and updates the `tracks`
    // prop from the parent (e.g. session/[id]/+page.svelte's onMessage
    // handler assigning `tracks = typed.data.tracks`).
    const broadcastTracks = [t3, t2, t1];
    await rerender({
      tracks: broadcastTracks,
      participants: [],
      onReorder,
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    await waitFor(() => {
      const titles = screen
        .getAllByText(/Song (One|Two|Three)/)
        .map((el) => el.textContent);
      expect(titles).toEqual(["Song Three", "Song Two", "Song One"]);
    });

    // Now the in-flight reorder rejects. Since the broadcast already
    // superseded our optimistic state, the revert must be skipped so the
    // broadcast-derived order isn't clobbered by the stale pre-reorder
    // snapshot.
    rejectOnReorder!(new Error("boom"));

    await waitFor(() =>
      expect(screen.getByText(/failed to reorder/i)).toBeTruthy(),
    );

    const titles = screen
      .getAllByText(/Song (One|Two|Three)/)
      .map((el) => el.textContent);
    expect(titles).toEqual(["Song Three", "Song Two", "Song One"]);
  });

  it("renders tracks in given order with resolved uploader names", () => {
    const tracks = [
      makeTrack({
        id: "t1",
        title: "Song One",
        requested_by_display_name: "Alice",
      }),
      makeTrack({
        id: "t2",
        title: "Song Two",
        requested_by_display_name: "Bob",
      }),
    ];
    render(QueueList, {
      tracks,
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    const titles = screen
      .getAllByText(/Song (One|Two)/)
      .map((el) => el.textContent);
    expect(titles).toEqual(["Song One", "Song Two"]);
    expect(screen.getByText(/Added by Alice/)).toBeTruthy();
    expect(screen.getByText(/Added by Bob/)).toBeTruthy();
  });

  it("falls back to resolving uploader name from participants when display name is null", () => {
    const tracks = [
      makeTrack({
        id: "t1",
        title: "Song One",
        requested_by_display_name: null,
        requested_by_client_id: "client-42",
      }),
    ];
    render(QueueList, {
      tracks,
      participants: [{ client_id: "client-42", display_name: "Charlie" }],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    expect(screen.getByText(/Added by Charlie/)).toBeTruthy();
  });

  it("falls back to a truncated client id when no display name is resolvable", () => {
    const tracks = [
      makeTrack({
        id: "t1",
        title: "Song One",
        requested_by_display_name: null,
        requested_by_client_id: "unresolvable-client-id",
      }),
    ];
    render(QueueList, {
      tracks,
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    expect(screen.getByText(/Added by unresolv/)).toBeTruthy();
  });

  it("calls onReorder with the expected id list when the queue is reordered", async () => {
    const tracks = [
      makeTrack({ id: "t1", title: "Song One" }),
      makeTrack({ id: "t2", title: "Song Two" }),
    ];
    const onReorder = vi.fn(() => Promise.resolve());
    const { container } = render(QueueList, {
      tracks,
      participants: [],
      onReorder,
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    // svelte-dnd-action drives reordering via consider/finalize CustomEvents
    // dispatched on the dndzone container; simulate a drag-completion by
    // dispatching a finalize event with the new item order directly, since
    // full pointer-based drag simulation is unreliable in jsdom.
    const list = container.querySelector("ul.tracks") as HTMLElement;
    const reordered = [tracks[1], tracks[0]];
    const finalizeEvent = new CustomEvent("finalize", {
      detail: {
        items: reordered,
        info: { trigger: "test", id: "t2", source: "test" },
      },
    });
    list.dispatchEvent(finalizeEvent);

    await waitFor(() => expect(onReorder).toHaveBeenCalledWith(["t2", "t1"]));
  });

  it("reverts to the original order and shows an error message when onReorder rejects", async () => {
    const tracks = [
      makeTrack({ id: "t1", title: "Song One" }),
      makeTrack({ id: "t2", title: "Song Two" }),
    ];
    const onReorder = vi.fn(() => Promise.reject(new Error("boom")));
    const { container } = render(QueueList, {
      tracks,
      participants: [],
      onReorder,
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    const list = container.querySelector("ul.tracks") as HTMLElement;
    const reordered = [tracks[1], tracks[0]];
    const finalizeEvent = new CustomEvent("finalize", {
      detail: {
        items: reordered,
        info: { trigger: "test", id: "t2", source: "test" },
      },
    });
    list.dispatchEvent(finalizeEvent);

    await waitFor(() =>
      expect(screen.getByText(/failed to reorder/i)).toBeTruthy(),
    );

    const titles = screen
      .getAllByText(/Song (One|Two)/)
      .map((el) => el.textContent);
    expect(titles).toEqual(["Song One", "Song Two"]);
  });

  it("shows a Play button only for ready tracks and invokes onPlay when clicked", async () => {
    const readyTrack = makeTrack({
      id: "t1",
      title: "Song One",
      status: "ready",
    });
    const pendingTrack = makeTrack({
      id: "t2",
      title: "Song Two",
      status: "pending",
    });
    const onPlay = vi.fn();
    render(QueueList, {
      tracks: [readyTrack, pendingTrack],
      participants: [],
      onReorder: vi.fn(),
      onPlay,
      onRemove: vi.fn(),
    });

    const playButtons = screen.getAllByRole("button", { name: /play/i });
    expect(playButtons).toHaveLength(1);

    await fireEvent.click(playButtons[0]);

    expect(onPlay).toHaveBeenCalledWith(readyTrack);
  });

  it("labels the play button 'Play' for the host and 'Play on host' otherwise", () => {
    const readyTrack = makeTrack({
      id: "t1",
      title: "Song One",
      status: "ready",
    });

    const { unmount: unmountHost } = render(QueueList, {
      tracks: [readyTrack],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
      isHost: true,
    });
    expect(screen.getByRole("button", { name: "Play" })).toBeTruthy();
    unmountHost();

    render(QueueList, {
      tracks: [readyTrack],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
      isHost: false,
    });
    expect(screen.getByRole("button", { name: "Play on host" })).toBeTruthy();
  });

  it("shows a Now Playing badge for the matching track reflecting isPlaying", () => {
    const t1 = makeTrack({ id: "t1", title: "Song One", status: "ready" });
    const t2 = makeTrack({ id: "t2", title: "Song Two", status: "ready" });

    const { rerender } = render(QueueList, {
      tracks: [t1, t2],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
      nowPlayingTrackId: "t1",
      isPlaying: true,
    });

    expect(screen.getByLabelText("Now playing")).toBeTruthy();

    rerender({
      tracks: [t1, t2],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
      nowPlayingTrackId: "t1",
      isPlaying: false,
    });

    expect(screen.getByLabelText("Now paused")).toBeTruthy();
  });

  it("does not show a Now Playing badge when no track matches nowPlayingTrackId", () => {
    const t1 = makeTrack({ id: "t1", title: "Song One", status: "ready" });
    render(QueueList, {
      tracks: [t1],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
      nowPlayingTrackId: null,
      isPlaying: false,
    });

    expect(screen.queryByText(/Now Playing/)).toBeNull();
  });

  it("renders a Remove button per item regardless of status", () => {
    const readyTrack = makeTrack({
      id: "t1",
      title: "Song One",
      status: "ready",
    });
    const pendingTrack = makeTrack({
      id: "t2",
      title: "Song Two",
      status: "pending",
    });
    render(QueueList, {
      tracks: [readyTrack, pendingTrack],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove: vi.fn(),
    });

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    expect(removeButtons).toHaveLength(2);
  });

  it("optimistically removes an item and calls onRemove when clicked", async () => {
    const t1 = makeTrack({ id: "t1", title: "Song One" });
    const t2 = makeTrack({ id: "t2", title: "Song Two" });
    const onRemove = vi.fn(() => Promise.resolve());
    render(QueueList, {
      tracks: [t1, t2],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove,
    });

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    await fireEvent.click(removeButtons[0]);

    expect(onRemove).toHaveBeenCalledWith(t1);
    await waitFor(() => {
      expect(screen.queryByText("Song One")).toBeNull();
    });
    expect(screen.getByText("Song Two")).toBeTruthy();
  });

  it("restores the item and shows an error message when onRemove rejects", async () => {
    const t1 = makeTrack({ id: "t1", title: "Song One" });
    const t2 = makeTrack({ id: "t2", title: "Song Two" });
    const onRemove = vi.fn(() => Promise.reject(new Error("boom")));
    render(QueueList, {
      tracks: [t1, t2],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove,
    });

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    await fireEvent.click(removeButtons[0]);

    await waitFor(() =>
      expect(screen.getByText(/failed to remove/i)).toBeTruthy(),
    );

    const titles = screen
      .getAllByText(/Song (One|Two)/)
      .map((el) => el.textContent);
    expect(titles).toEqual(["Song One", "Song Two"]);
  });

  it("does not clobber a newer broadcast update when its own remove rejects", async () => {
    const t1 = makeTrack({ id: "t1", title: "Song One" });
    const t2 = makeTrack({ id: "t2", title: "Song Two" });
    const t3 = makeTrack({ id: "t3", title: "Song Three" });

    let rejectOnRemove: (err: Error) => void;
    const onRemove = vi.fn(
      () =>
        new Promise<void>((_resolve, reject) => {
          rejectOnRemove = reject;
        }),
    );

    const { rerender } = render(QueueList, {
      tracks: [t1, t2, t3],
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove,
    });

    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    await fireEvent.click(removeButtons[0]);

    await waitFor(() => expect(onRemove).toHaveBeenCalledWith(t1));

    // While the DELETE is still in flight, a track_removed broadcast (from
    // another member's concurrent removal) arrives and updates the `tracks`
    // prop from the parent — say it removed t2 instead.
    const broadcastTracks = [t1, t3];
    await rerender({
      tracks: broadcastTracks,
      participants: [],
      onReorder: vi.fn(),
      onPlay: vi.fn(),
      onRemove,
    });

    await waitFor(() => {
      const titles = screen
        .getAllByText(/Song (One|Two|Three)/)
        .map((el) => el.textContent);
      expect(titles).toEqual(["Song One", "Song Three"]);
    });

    // Now the in-flight remove rejects. Since the broadcast already
    // superseded our optimistic state, the revert must be skipped so the
    // broadcast-derived list isn't clobbered by our stale snapshot.
    rejectOnRemove!(new Error("boom"));

    await waitFor(() =>
      expect(screen.getByText(/failed to remove/i)).toBeTruthy(),
    );

    const titles = screen
      .getAllByText(/Song (One|Two|Three)/)
      .map((el) => el.textContent);
    expect(titles).toEqual(["Song One", "Song Three"]);
  });
});
