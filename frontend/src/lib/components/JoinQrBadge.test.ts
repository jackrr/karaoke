import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import JoinQrBadge from "./JoinQrBadge.svelte";

function setup() {
  return render(JoinQrBadge, {
    joinUrl: "https://example.com/join?code=123456",
    code: "123456",
  });
}

describe("JoinQrBadge", () => {
  it("shows the QR code and formatted code", () => {
    const { container, getByText } = setup();

    expect(container.querySelector("svg")).toBeTruthy();
    expect(getByText("123 456")).toBeTruthy();
  });
});
