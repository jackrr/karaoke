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
