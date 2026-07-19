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
  it("renders all lines", () => {
    const { getByText } = render(LyricsDisplay, { lines, currentTime: 0 });
    expect(getByText("First line")).toBeTruthy();
    expect(getByText("Second line")).toBeTruthy();
    expect(getByText("Third line")).toBeTruthy();
  });

  it("marks the line at or before currentTime as active", () => {
    const { getByText } = render(LyricsDisplay, { lines, currentTime: 4 });
    expect(getByText("Second line").classList.contains("active")).toBe(true);
    expect(getByText("First line").classList.contains("active")).toBe(false);
    expect(getByText("Third line").classList.contains("active")).toBe(false);
  });

  it("moves the active line forward when rerendered with a later currentTime", async () => {
    const { getByText, rerender } = render(LyricsDisplay, {
      lines,
      currentTime: 4,
    });
    expect(getByText("Second line").classList.contains("active")).toBe(true);

    await rerender({ lines, currentTime: 6 });

    expect(getByText("Third line").classList.contains("active")).toBe(true);
    expect(getByText("Second line").classList.contains("active")).toBe(false);
  });
});
