/**
 * Entry point for the Bun + Vite frontend.
 *
 * Bootstraps the root component (layout + home page) and mounts it
 * into the <div id="root"> element rendered by index.html.
 */
import { mount } from 'svelte';
import Layout from './routes/+layout.svelte';
import Home from './routes/+page.svelte';

mount(Layout, {
  target: document.getElementById('root')!,
  props: { default: Home },
});
