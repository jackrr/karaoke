<script lang="ts">
  import { themeStore } from '../theme.svelte';
</script>

<button
  class="theme-toggle"
  type="button"
  onclick={() => themeStore.toggle()}
  aria-label={themeStore.current === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
>
  {themeStore.current === 'dark' ? '🌙 Dark' : '☀️ Light'}
</button>

<style>
  .theme-toggle {
    min-height: 44px;
    padding: 0.5rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-surface-muted);
    color: var(--color-text);
    font-size: 1rem;
    cursor: pointer;
  }
</style>
