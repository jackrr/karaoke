import { describe, it, expect } from "vitest";
import { render, waitFor } from "@testing-library/svelte";
import LyricsDisplay from "./LyricsDisplay.svelte";
import type { LrcLine } from "../utils/lrc";

const lines: LrcLine[] = [
  { time: 1, text: "First line" },
  { time: 3, text: "Second line" },
  { time: 5, text: "Third line" },
];

describe("LyricsDisplay", () => {
  it("renders the current line", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line")).toBeTruthy();
  });

  it("previews the previous line above the current line", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line").className).toContain("current-line");
    expect(getByText("First line").className).toContain("previous-line");
  });

  it("shows no previous line before the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(getByText("First line").className).not.toContain("previous-line");
  });

  it("shows no previous line on the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 1,
    });
    expect(getByText("First line").className).not.toContain("previous-line");
  });

  it("shows a placeholder before the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(getByText("♪")).toBeTruthy();
  });

  it("moves the current line forward when rerendered with a later currentTime", async () => {
    const { getByText, rerender } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line")).toBeTruthy();

    await rerender({ lines, currentTime: 6 });

    await waitFor(() => expect(getByText("Third line")).toBeTruthy());
    await waitFor(() =>
      expect(getByText("Third line").className).toContain("current-line"),
    );
  });

  it("previews the next line beneath the current line", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 1,
    });
    expect(getByText("First line").className).toContain("current-line");
    expect(getByText("Second line").className).toContain("next-line");
  });

  it("shows no next-line preview after the last line", () => {
    const { getByText, queryByText } = render(LyricsDisplay, {
      lines,
      currentTime: 5,
    });
    expect(getByText("Third line").className).toContain("current-line");
    expect(getByText("Second line").className).toContain("previous-line");
    expect(queryByText("First line")).toBeNull();
  });

  it("shows the first line as a preview before the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(getByText("First line").className).toContain("next-line");
  });
});
