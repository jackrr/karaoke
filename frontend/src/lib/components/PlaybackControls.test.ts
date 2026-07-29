import { describe, it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import PlaybackControls from "./PlaybackControls.svelte";

/**
 * A minimal fake audio element: real jsdom `<audio>` elements log
 * "not implemented" for play()/pause(), so we drive the component through a
 * plain EventTarget that mimics the bits of HTMLAudioElement it touches.
 */
type FakeAudio = EventTarget & {
  paused: boolean;
  currentTime: number;
  duration: number;
  play: () => void;
  pause: () => void;
};

function makeFakeAudio(): FakeAudio {
  const target = new EventTarget() as FakeAudio;
  target.paused = true;
  target.currentTime = 0;
  target.duration = 100;
  target.play = vi.fn(() => {
    target.paused = false;
    target.dispatchEvent(new Event("play"));
  });
  target.pause = vi.fn(() => {
    target.paused = true;
    target.dispatchEvent(new Event("pause"));
  });
  return target;
}

function asAudioElement(fake: FakeAudio): HTMLAudioElement {
  return fake as unknown as HTMLAudioElement;
}

describe("PlaybackControls", () => {
  it("toggles play/pause when the button is clicked", async () => {
    const audio = makeFakeAudio();
    const { getByRole } = render(PlaybackControls, {
      audio: asAudioElement(audio),
      onStop: vi.fn(),
    });

    const button = getByRole("button", { name: "Play" });
    await fireEvent.click(button);
    expect(audio.play).toHaveBeenCalled();

    await fireEvent.click(getByRole("button", { name: "Pause" }));
    expect(audio.pause).toHaveBeenCalled();
  });

  it("formats elapsed and total time as mm:ss", async () => {
    const audio = makeFakeAudio();
    audio.duration = 125;
    audio.dispatchEvent(new Event("loadedmetadata"));
    audio.currentTime = 65;
    audio.dispatchEvent(new Event("timeupdate"));

    const { getByText } = render(PlaybackControls, {
      audio: asAudioElement(audio),
      onStop: vi.fn(),
    });
    audio.dispatchEvent(new Event("loadedmetadata"));
    audio.dispatchEvent(new Event("timeupdate"));

    expect(getByText("1:05")).toBeTruthy();
    expect(getByText("2:05")).toBeTruthy();
  });

  it("falls back to 0:00 total time when duration is not yet finite", async () => {
    const audio = makeFakeAudio();
    audio.duration = NaN;

    const { getAllByText } = render(PlaybackControls, {
      audio: asAudioElement(audio),
      onStop: vi.fn(),
    });
    audio.dispatchEvent(new Event("loadedmetadata"));

    // currentTime and duration are both 0:00 here, so two matches are expected.
    expect(getAllByText("0:00")).toHaveLength(2);

    audio.duration = Infinity;
    audio.dispatchEvent(new Event("loadedmetadata"));

    expect(getAllByText("0:00")).toHaveLength(2);
  });

  it("updates currentTime when the seek input changes", async () => {
    const audio = makeFakeAudio();
    const { getByRole } = render(PlaybackControls, {
      audio: asAudioElement(audio),
      onStop: vi.fn(),
    });

    const seek = getByRole("slider", { name: "Seek" }) as HTMLInputElement;
    await fireEvent.input(seek, { target: { value: "42" } });

    expect(audio.currentTime).toBe(42);
  });

  it("calls onStop and pauses/resets the audio when Stop is clicked", async () => {
    const audio = makeFakeAudio();
    audio.paused = false;
    audio.currentTime = 30;
    const onStop = vi.fn();
    const { getByRole } = render(PlaybackControls, {
      audio: asAudioElement(audio),
      onStop,
    });

    await fireEvent.click(getByRole("button", { name: "Stop" }));

    expect(audio.pause).toHaveBeenCalled();
    expect(audio.currentTime).toBe(0);
    expect(onStop).toHaveBeenCalled();
  });
});
