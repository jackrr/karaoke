import '@testing-library/jest-dom/vitest';

// Polyfill requestAnimationFrame / cancelAnimationFrame for jsdom
globalThis.requestAnimationFrame = (cb: (...args: unknown[]) => void) =>
  setTimeout(cb, 0);
globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id);
