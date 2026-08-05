<script lang="ts">
  import { setContext } from 'svelte';
  import { SESSION_MENU_TRIGGER_KEY, type SessionMenuTrigger } from '$lib/sessionMenuTrigger';

  const trigger: SessionMenuTrigger = $state({ open: null });
  setContext(SESSION_MENU_TRIGGER_KEY, trigger);
</script>

<div class="session-layout">
  <nav class="title-row">
    <a href="/">← Home</a>
    {#if trigger.open}
      <button class="menu-trigger" type="button" onclick={trigger.open} aria-label="Open menu">
        ☰
      </button>
    {/if}
  </nav>
  <slot />
</div>

<style>
  :global(.session-layout) {
    display: flex;
    flex-direction: column;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem;
    min-width: 0;
  }

  .title-row {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1rem;
  }

  :global(.session-layout a) {
    color: var(--color-text);
    text-decoration: none;
  }

  .menu-trigger {
    margin-left: auto;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-surface);
    font-size: 1.1rem;
    cursor: pointer;
  }
</style>