import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/svelte";
import SessionSettings from "./SessionSettings.svelte";

describe("SessionSettings", () => {
  it("renders with the initial value", () => {
    render(SessionSettings, { vocalVolumeFraction: 0.2, onUpdate: vi.fn() });
    const input = screen.getByLabelText(
      /background vocal gain/i,
    ) as HTMLInputElement;
    expect(input.value).toBe("0.2");
    expect(screen.getByText(/0\.20/)).toBeTruthy();
  });

  it("updates the slider and submits the new value", async () => {
    const onUpdate = vi.fn(() => Promise.resolve());
    render(SessionSettings, { vocalVolumeFraction: 0.2, onUpdate });

    const input = screen.getByLabelText(/background vocal gain/i);
    await fireEvent.input(input, { target: { value: "0.8" } });
    await fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onUpdate).toHaveBeenCalledWith(0.8);
  });

  it("shows an error message when onUpdate rejects", async () => {
    const onUpdate = vi.fn(() => Promise.reject(new Error("boom")));
    render(SessionSettings, { vocalVolumeFraction: 0.2, onUpdate });

    await fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(screen.getByText(/failed to save/i)).toBeTruthy(),
    );
  });

  it("preserves the edited value after a failed save", async () => {
    const onUpdate = vi.fn(() => Promise.reject(new Error("boom")));
    render(SessionSettings, { vocalVolumeFraction: 0.2, onUpdate });

    const input = screen.getByLabelText(
      /background vocal gain/i,
    ) as HTMLInputElement;
    await fireEvent.input(input, { target: { value: "0.8" } });
    await fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(screen.getByText(/failed to save/i)).toBeTruthy(),
    );
    expect(input.value).toBe("0.8");
  });
});
