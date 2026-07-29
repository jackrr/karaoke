import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import SessionMenu from "./SessionMenu.svelte";

function setup(overrides: Partial<Parameters<typeof SessionMenu>[1]> = {}) {
  const onSendMessage = vi.fn();
  const onLeave = vi.fn();
  const result = render(SessionMenu, {
    messages: [{ sender: "Alice", text: "hi" }],
    onSendMessage,
    onLeave,
    ...overrides,
  });
  return { ...result, onSendMessage, onLeave };
}

describe("SessionMenu", () => {
  it("is closed initially and open() opens it", () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    expect(dialog.hasAttribute("open")).toBe(false);

    component.open();

    expect(dialog.hasAttribute("open")).toBe(true);
  });

  it("close() closes it", () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    component.close();

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("Escape closes the dialog", async () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    await fireEvent.keyDown(dialog, { key: "Escape" });

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("clicking the backdrop (the dialog element itself) closes it", async () => {
    const { component, container } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();
    expect(dialog.hasAttribute("open")).toBe(true);

    await fireEvent.click(dialog);

    expect(dialog.hasAttribute("open")).toBe(false);
  });

  it("clicking inside the menu content does not close it", async () => {
    const { component, container, getByText } = setup();
    const dialog = container.querySelector("dialog")!;
    component.open();

    await fireEvent.click(getByText("hi"));

    expect(dialog.hasAttribute("open")).toBe(true);
  });

  it("renders Chat content", () => {
    const { getByText } = setup();
    expect(getByText("hi")).toBeTruthy();
  });

  it("fires onLeave when Leave Session is clicked", async () => {
    const { component, getByRole, onLeave } = setup();
    component.open();
    await fireEvent.click(getByRole("button", { name: "Leave Session" }));
    expect(onLeave).toHaveBeenCalled();
  });

  it("fires onSendMessage when a chat message is sent", async () => {
    const { component, getByPlaceholderText, getByRole, onSendMessage } =
      setup();
    component.open();
    await fireEvent.input(getByPlaceholderText("Type a message..."), {
      target: { value: "hello" },
    });
    await fireEvent.click(getByRole("button", { name: "Send" }));
    expect(onSendMessage).toHaveBeenCalledWith("hello");
  });
});
