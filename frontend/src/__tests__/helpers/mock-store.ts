import { writable } from 'svelte/store';

/** Create writable stores without triggering SvelteKit's $app/stores.
 *  Used for testing modules that import from `$lib/store`. */
export function mockWritable(initial: unknown) {
  return writable(initial);
}

// Global store-like interface for modules that subscribe directly
export interface WritableLike<T> {
  subscribe: (run: (v: T) => void) => () => void;
  set: (v: T) => void;
}
