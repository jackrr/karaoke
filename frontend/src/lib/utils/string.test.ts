import { describe, it, expect } from "vitest";
import { formatCode, buildJoinUrl } from "./string";

describe("formatCode", () => {
  it("formats a 6-digit code", () => {
    expect(formatCode("123456")).toBe("123 456");
  });

  it("handles shorter codes", () => {
    expect(formatCode("12")).toBe("12");
    expect(formatCode("1234")).toBe("123 4");
  });
});

describe("buildJoinUrl", () => {
  it("builds a join link with the code as a query param", () => {
    expect(buildJoinUrl("https://example.com", "123456")).toBe(
      "https://example.com/join?code=123456",
    );
  });
});
