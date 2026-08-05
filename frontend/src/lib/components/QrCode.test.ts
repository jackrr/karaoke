import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import QrCode from "./QrCode.svelte";

describe("QrCode", () => {
  it("renders an svg with role img", () => {
    const { container } = render(QrCode, {
      value: "https://example.com/join?code=123456",
    });
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
    expect(svg?.getAttribute("role")).toBe("img");
  });

  it("renders different content for different values", () => {
    const { container: a } = render(QrCode, {
      value: "https://example.com/join?code=111111",
    });
    const { container: b } = render(QrCode, {
      value: "https://example.com/join?code=222222",
    });
    expect(a.querySelector("svg")?.innerHTML).not.toBe(
      b.querySelector("svg")?.innerHTML,
    );
  });
});
