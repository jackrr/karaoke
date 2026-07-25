import { describe, it, expect } from "vitest";
import { formatCode } from "./string";

describe("formatCode", () => {
  it("formats a 6-digit code", () => {
    expect(formatCode("123456")).toBe("123 456");
  });

  it("handles shorter codes", () => {
    expect(formatCode("12")).toBe("12");
    expect(formatCode("1234")).toBe("123 4");
  });
});
