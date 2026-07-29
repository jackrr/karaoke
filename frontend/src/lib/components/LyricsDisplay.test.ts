import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import LyricsDisplay from "./LyricsDisplay.svelte";
import type { LrcLine } from "../utils/lrc";

const lines: LrcLine[] = [
  { time: 1, text: "First line" },
  { time: 3, text: "Second line" },
  { time: 5, text: "Third line" },
];

describe("LyricsDisplay", () => {
  it("renders only the current line", () => {
    const { getByText, queryByText } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line")).toBeTruthy();
    expect(queryByText("First line")).toBeNull();
    expect(queryByText("Third line")).toBeNull();
  });

  it("shows a placeholder before the first cue", () => {
    const { getByText, queryByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(getByText("♪")).toBeTruthy();
    expect(queryByText("First line")).toBeNull();
  });

  it("moves the current line forward when rerendered with a later currentTime", async () => {
    const { getByText, queryByText, rerender } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line")).toBeTruthy();

    await rerender({ lines, currentTime: 6 });

    expect(getByText("Third line")).toBeTruthy();
    expect(queryByText("Second line")).toBeNull();
  });
});
