import { describe, it, expect } from "vitest";
import { render, waitFor } from "@testing-library/svelte";
import LyricsDisplay from "./LyricsDisplay.svelte";
import type { LrcLine } from "../utils/lrc";

const lines: LrcLine[] = [
  { time: 1, text: "First line" },
  { time: 3, text: "Second line" },
  { time: 5, text: "Third line" },
];

function offsetOf(el: HTMLElement): string {
  return el.style.getPropertyValue("--offset");
}

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
    expect(getByText("Second line").className).toContain("current");
    expect(offsetOf(getByText("First line"))).toBe("-1");
  });

  it("shows no previous line before the first cue", () => {
    const { queryByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(offsetOf(queryByText("First line")!)).not.toBe("-1");
  });

  it("shows no previous line on the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 1,
    });
    expect(offsetOf(getByText("First line"))).toBe("0");
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
      expect(getByText("Third line").className).toContain("current"),
    );
  });

  it("previews the next line beneath the current line", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 1,
    });
    expect(getByText("First line").className).toContain("current");
    expect(offsetOf(getByText("Second line"))).toBe("1");
  });

  it("shows no next-line preview after the last line", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 5,
    });
    expect(getByText("Third line").className).toContain("current");
    expect(offsetOf(getByText("Second line"))).toBe("-1");
    expect(getByText("First line").className).toContain("far");
  });

  it("shows the first line as a preview before the first cue", () => {
    const { getByText } = render(LyricsDisplay, {
      lines,
      currentTime: 0,
    });
    expect(offsetOf(getByText("First line"))).toBe("1");
  });
});
