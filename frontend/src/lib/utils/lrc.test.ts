import { describe, it, expect } from "vitest";
import { parseLrc, findCurrentLineIndex } from "./lrc";

describe("parseLrc", () => {
  it("parses a multi-line sample matching vtt_to_lrc output format", () => {
    const content = "[00:01.00]Hello\n[00:03.50]World";
    expect(parseLrc(content)).toEqual([
      { time: 1, text: "Hello" },
      { time: 3.5, text: "World" },
    ]);
  });

  it("skips metadata lines and blank lines", () => {
    const content =
      "[ar:Artist]\n\n[00:01.00]Hello\n[ti:Title]\n[00:02.00]World\n";
    expect(parseLrc(content)).toEqual([
      { time: 1, text: "Hello" },
      { time: 2, text: "World" },
    ]);
  });

  it("skips timestamp lines with no text", () => {
    const content = "[00:01.00]\n[00:02.00]World";
    expect(parseLrc(content)).toEqual([{ time: 2, text: "World" }]);
  });

  it("sorts out-of-order input by time", () => {
    const content = "[00:05.00]Later\n[00:01.00]Earlier";
    expect(parseLrc(content)).toEqual([
      { time: 1, text: "Earlier" },
      { time: 5, text: "Later" },
    ]);
  });
});

describe("findCurrentLineIndex", () => {
  const lines = [
    { time: 1, text: "one" },
    { time: 3, text: "two" },
    { time: 5, text: "three" },
  ];

  it("returns -1 before the first line", () => {
    expect(findCurrentLineIndex(lines, 0)).toBe(-1);
  });

  it("returns the index of an exact match", () => {
    expect(findCurrentLineIndex(lines, 3)).toBe(1);
  });

  it("returns the previous line's index when between two lines", () => {
    expect(findCurrentLineIndex(lines, 4)).toBe(1);
  });

  it("returns the last line's index after the last line", () => {
    expect(findCurrentLineIndex(lines, 100)).toBe(2);
  });
});
