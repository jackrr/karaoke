<script lang="ts">
  import '../app.css';
  import { setContext } from 'svelte';
  import { SESSION_MENU_TRIGGER_KEY, type SessionMenuTrigger } from '$lib/sessionMenuTrigger';
  import AppMenu from '$lib/components/AppMenu.svelte';

  const trigger: SessionMenuTrigger = $state({ open: null });
  setContext(SESSION_MENU_TRIGGER_KEY, trigger);

  let appMenu: { open: () => void } | undefined = $state();

  function handleMenuClick() {
    if (trigger.open) trigger.open();
    else appMenu?.open();
  }
</script>

<style>
  .navbar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem 2rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .navbar > a:hover {
    text-decoration: underline;
  }

  .menu-trigger {
    margin-left: auto;
    min-width: 44px;
    min-height: 44px;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    background: var(--color-surface-muted);
    color: var(--color-text);
    font-size: 1.1rem;
    cursor: pointer;
  }

  main {
    padding: 2rem;
    max-width: 960px;
    margin: 0 auto;
    min-width: 0;
  }
</style>

<nav class="navbar">
  <a href="/">Karaoke</a>
  <button class="menu-trigger" type="button" onclick={handleMenuClick} aria-label="Open menu">
    ☰
  </button>
</nav>

<main>
  <slot />
</main>

<AppMenu bind:this={appMenu} />
