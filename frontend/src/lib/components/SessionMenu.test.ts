import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { tick } from "svelte";
import SessionMenu from "./SessionMenu.svelte";
import type { Track } from "../api";

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
    requested_by_display_name: null,
    position: 0,
    created_at: "now",
    updated_at: "now",
    ...overrides,
  };
}

function setup(overrides: Partial<Parameters<typeof SessionMenu>[1]> = {}) {
  const onSendMessage = vi.fn();
  const onLeave = vi.fn();
  const onSubmitTrack = vi.fn();
  const onReorder = vi.fn();
  const onPlay = vi.fn();
  const onRemove = vi.fn();
  const result = render(SessionMenu, {
    messages: [{ sender: "Alice", text: "hi" }],
    onSendMessage,
    onLeave,
    tracks: [],
    participants: [],
    onSubmitTrack,
    onReorder,
    onPlay,
    onRemove,
    ...overrides,
  });
  return {
    ...result,
    onSendMessage,
    onLeave,
    onSubmitTrack,
    onReorder,
    onPlay,
    onRemove,
  };
}

describe("SessionMenu", () => {
  it("is closed initially and open() opens it", () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    expect(dialog.hasAttribute("open")).toBe(false);

    component.open();

    expect(dialog.hasAttribute("open")).toBe(true);
  });

  it("close() closes it", () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    component.close();

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("Escape closes the dialog", async () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    await fireEvent.keyDown(dialog, { key: "Escape" });

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("clicking the backdrop (the dialog element itself) closes it", async () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    await fireEvent.click(dialog);

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("clicking inside the menu content does not close it", async () => {
    const { component, container, getByText } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    await tick();

    await fireEvent.click(getByText("hi"));

    expect(dialog.hasAttribute("open")).toBe(true);
  });

  it("renders Chat content", async () => {
    const { component, getByText } = setup();
    component.open();
    await tick();
    expect(getByText("hi")).toBeTruthy();
  });

  it("fires onLeave when Leave Session is clicked", async () => {
    const { component, getByRole, onLeave } = setup();
    component.open();
    await tick();
    await fireEvent.click(getByRole("button", { name: "Leave Session" }));
    expect(onLeave).toHaveBeenCalled();
  });

  it("fires onSendMessage when a chat message is sent", async () => {
    const { component, getByPlaceholderText, getByRole, onSendMessage } =
      setup();
    component.open();
    await tick();
    await fireEvent.input(getByPlaceholderText("Type a message..."), {
      target: { value: "hello" },
    });
    await fireEvent.click(getByRole("button", { name: "Send" }));
    expect(onSendMessage).toHaveBeenCalledWith("hello");
  });

  it("renders the add-track form and submits the trimmed URL", async () => {
    const onSubmitTrack = vi.fn(() => Promise.resolve(makeTrack()));
    const { component, getByPlaceholderText, getByRole } = setup({
      onSubmitTrack,
    });
    component.open();
    await tick();

    await fireEvent.input(getByPlaceholderText("Paste a YouTube URL..."), {
      target: { value: "  https://youtube.com/watch?v=xyz  " },
    });
    await fireEvent.click(getByRole("button", { name: /add track/i }));

    expect(onSubmitTrack).toHaveBeenCalledWith(
      "https://youtube.com/watch?v=xyz",
    );
  });

  it("does not mount its queue list while closed", () => {
    const { queryByText } = setup({
      tracks: [makeTrack({ id: "t1", title: "Song One" })],
    });
    expect(queryByText("Song One")).toBeNull();
  });

  it("renders the queue list given tracks", async () => {
    const { component, getByText } = setup({
      tracks: [makeTrack({ id: "t1", title: "Song One" })],
    });
    component.open();
    await tick();

    expect(getByText("Song One")).toBeTruthy();
  });

  it("closes the dialog when Play is clicked from the queue list", async () => {
    const onPlay = vi.fn();
    const { component, container, getByRole } = setup({
      tracks: [makeTrack({ id: "t1", title: "Song One", status: "ready" })],
      onPlay,
    });
    const dialog = container.querySelector("dialog")!;
    component.open();
    await tick();

    await fireEvent.click(getByRole("button", { name: "Play" }));

    expect(onPlay).toHaveBeenCalled();
    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("closes the dialog when Remove is clicked from the queue list", async () => {
    const onRemove = vi.fn(() => Promise.resolve());
    const { component, container, getByRole } = setup({
      tracks: [makeTrack({ id: "t1", title: "Song One" })],
      onRemove,
    });
    const dialog = container.querySelector("dialog")!;
    component.open();
    await tick();

    await fireEvent.click(getByRole("button", { name: "Remove" }));

    expect(onRemove).toHaveBeenCalled();
    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("keeps the dialog open after a successful track submit", async () => {
    const onSubmitTrack = vi.fn(() => Promise.resolve(makeTrack()));
    const { component, container, getByPlaceholderText, getByRole } = setup({
      onSubmitTrack,
    });
    const dialog = container.querySelector("dialog")!;
    component.open();
    await tick();

    await fireEvent.input(getByPlaceholderText("Paste a YouTube URL..."), {
      target: { value: "https://youtube.com/watch?v=xyz" },
    });
    await fireEvent.click(getByRole("button", { name: /add track/i }));

    await waitFor(() => expect(onSubmitTrack).toHaveBeenCalled());
    expect(dialog.hasAttribute("open")).toBe(true);
  });
});
