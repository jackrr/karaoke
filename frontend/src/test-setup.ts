// jsdom doesn't implement the Web Animations API, but Svelte 5's transition
// runtime calls `element.animate()` under the hood for `in:`/`out:`
// directives. Stub it so components using transitions can be rendered in
// tests; it resolves immediately rather than animating over real time.
if (typeof Element !== "undefined" && !Element.prototype.animate) {
  Element.prototype.animate = function (this: Element): globalThis.Animation {
    const animation = {
      currentTime: 0,
      playState: "running",
      onfinish: null as (() => void) | null,
      oncancel: null as (() => void) | null,
      effect: null,
      cancel() {
        this.playState = "idle";
      },
      finish() {
        this.playState = "finished";
      },
    };
    setTimeout(() => {
      animation.playState = "finished";
      animation.onfinish?.();
    }, 0);
    return animation as unknown as globalThis.Animation;
  };
}

// jsdom doesn't implement ResizeObserver, used by components that measure
// overflow (e.g. the queue's marquee-scrolling track titles). Fire the
// callback once on a microtask after observe(), like a real resize
// notification after initial layout, so tests can stub element dimensions
// between render and the observer's first callback.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    #callback: ResizeObserverCallback;
    constructor(callback: ResizeObserverCallback) {
      this.#callback = callback;
    }
    observe(target: Element) {
      queueMicrotask(() =>
        this.#callback(
          [{ target } as ResizeObserverEntry],
          this as unknown as ResizeObserver,
        ),
      );
    }
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
}
