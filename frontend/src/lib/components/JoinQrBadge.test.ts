import { describe, it, expect } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import JoinQrBadge from "./JoinQrBadge.svelte";

function setup() {
  return render(JoinQrBadge, {
    joinUrl: "https://example.com/join?code=123456",
    code: "123456",
  });
}

describe("JoinQrBadge", () => {
  it("is collapsed by default", () => {
    const { container, getByRole } = setup();
    expect(container.querySelector("svg")).toBeNull();
    expect(getByRole("button", { name: /show qr code/i })).toBeTruthy();
  });

  it("expands to show the QR code and formatted code on click", async () => {
    const { container, getByRole, getByText } = setup();

    await fireEvent.click(getByRole("button", { name: /show qr code/i }));

    expect(container.querySelector("svg")).toBeTruthy();
    expect(getByText("123 456")).toBeTruthy();
  });

  it("collapses again when closed", async () => {
    const { container, getByRole } = setup();

    await fireEvent.click(getByRole("button", { name: /show qr code/i }));
    expect(container.querySelector("svg")).toBeTruthy();

    await fireEvent.click(getByRole("button", { name: /close qr code/i }));

    expect(container.querySelector("svg")).toBeNull();
  });
});
