<script lang="ts">
  import ThemeToggle from './ThemeToggle.svelte';

  let dialogEl: HTMLDialogElement | undefined = $state();
  let isOpen = $state(false);

  // jsdom (used in component tests) doesn't implement showModal()/close(),
  // so fall back to toggling the `open` attribute directly there.
  export function open() {
    const el = dialogEl;
    if (!el) return;
    if (typeof el.showModal === 'function') el.showModal();
    else el.setAttribute('open', '');
    isOpen = true;
  }

  export function close() {
    const el = dialogEl;
    if (!el) return;
    if (typeof el.close === 'function') el.close();
    else el.removeAttribute('open');
    isOpen = false;
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === dialogEl) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  function handleNativeClose() {
    isOpen = false;
  }
</script>

<dialog
  bind:this={dialogEl}
  class="app-menu"
  aria-label="Menu"
  onclick={handleBackdropClick}
  onkeydown={handleKeydown}
  onclose={handleNativeClose}
>
  <button class="close-btn" type="button" onclick={close} aria-label="Close menu">✕</button>

  {#if isOpen}
    <div class="menu-content">
      <h3>Theme</h3>
      <ThemeToggle />
    </div>
  {/if}
</dialog>

<style>
  .app-menu {
    --panel-width: min(90vw, 420px);
    position: fixed;
    top: 0;
    bottom: 0;
    left: auto;
    right: calc(-1 * var(--panel-width));
    margin: 0;
    height: 100%;
    max-height: 100%;
    width: var(--panel-width);
    border: none;
    padding: 1.5rem;
    background: var(--color-surface);
    color: var(--color-text);
    box-shadow: -4px 0 16px var(--color-shadow);
    transition: right 0.25s ease;
  }

  .app-menu[open] {
    right: 0;
  }

  .app-menu::backdrop {
    background: var(--color-overlay);
  }

  .close-btn {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    min-width: 44px;
    min-height: 44px;
    border: none;
    background: transparent;
    font-size: 1.1rem;
    cursor: pointer;
  }

  .menu-content {
    margin-top: 2.5rem;
  }

  .menu-content h3 {
    margin: 0 0 0.5rem;
  }
</style>
