import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

// Polyfill requestAnimationFrame / cancelAnimationFrame for jsdom
globalThis.requestAnimationFrame = (cb: (...args: unknown[]) => void) => setTimeout(cb, 0);
globalThis.cancelAnimationFrame = (id: number) => clearTimeout(id);

// Mock SvelteKit modules that are unavailable in tests
vi.mock('$app/environment', () => ({
  browser: false,
  dev: true,
  building: false,
  version: 'test',
}));

// Mock $app/navigation to prevent navigation errors
vi.mock('$app/navigation', () => ({
  goTo: vi.fn(),
  navigate: vi.fn(),
  prefetch: vi.fn(),
  prefetchDocs: vi.fn(),
  disableScrollHandling: vi.fn(),
}));

// Mock $app/stores
vi.mock('$app/stores', () => {
  const { writable } = require('svelte/store');
  const original = writable;
  return {
    page: original({ url: '', data: {}, form: '' }),
    navigating: original(null),
    session: original(null),
  };
});
