import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import Chat from "./Chat.svelte";

describe("Chat", () => {
  it("renders existing messages", () => {
    const { getByText } = render(Chat, {
      messages: [{ sender: "Alice", text: "hi there" }],
      onSend: vi.fn(),
    });

    expect(getByText("Alice:")).toBeTruthy();
    expect(getByText("hi there")).toBeTruthy();
  });

  it("renders no message list when there are no messages", () => {
    const { container } = render(Chat, { messages: [], onSend: vi.fn() });
    expect(container.querySelector(".messages")).toBeNull();
  });

  it("sends the trimmed draft and clears the input", async () => {
    const onSend = vi.fn();
    const { getByPlaceholderText, getByRole } = render(Chat, {
      messages: [],
      onSend,
    });

    const input = getByPlaceholderText("Type a message...") as HTMLInputElement;
    await fireEvent.input(input, { target: { value: "  hello  " } });
    await fireEvent.click(getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("hello");
    expect(input.value).toBe("");
  });

  it("does not send an empty or whitespace-only draft", async () => {
    const onSend = vi.fn();
    const { getByPlaceholderText, getByRole } = render(Chat, {
      messages: [],
      onSend,
    });

    const input = getByPlaceholderText("Type a message...") as HTMLInputElement;
    await fireEvent.input(input, { target: { value: "   " } });
    await fireEvent.click(getByRole("button", { name: "Send" }));

    expect(onSend).not.toHaveBeenCalled();
  });
});
