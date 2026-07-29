<script lang="ts">
  import Chat from './Chat.svelte';

  type ChatMessage = { sender: string; text: string; type?: string };

  let {
    messages,
    onSendMessage,
    onLeave,
  }: {
    messages: ChatMessage[];
    onSendMessage: (text: string) => void;
    onLeave: () => void;
  } = $props();

  let dialogEl: HTMLDialogElement | undefined = $state();

  // jsdom (used in component tests) doesn't implement showModal()/close(),
  // so fall back to toggling the `open` attribute directly there.
  export function open() {
    const el = dialogEl;
    if (!el) return;
    if (typeof el.showModal === 'function') el.showModal();
    else el.setAttribute('open', '');
  }

  export function close() {
    const el = dialogEl;
    if (!el) return;
    if (typeof el.close === 'function') el.close();
    else el.removeAttribute('open');
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === dialogEl) close();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

<dialog
  bind:this={dialogEl}
  class="session-menu"
  aria-label="Session menu"
  onclick={handleBackdropClick}
  onkeydown={handleKeydown}
>
  <button class="close-btn" type="button" onclick={close} aria-label="Close menu">✕</button>

  <div class="menu-content">
    <Chat {messages} onSend={onSendMessage} />
    <button class="btn btn-secondary leave-btn" type="button" onclick={onLeave}>
      Leave Session
    </button>
  </div>
</dialog>

<style>
  .session-menu {
    position: fixed;
    inset: 0 0 0 auto;
    margin: 0;
    height: 100%;
    max-height: 100%;
    width: 90vw;
    max-width: 420px;
    border: none;
    padding: 1.5rem;
    box-shadow: -4px 0 16px rgba(0, 0, 0, 0.15);
    transform: translateX(100%);
    transition: transform 0.25s ease;
  }

  .session-menu[open] {
    transform: translateX(0);
  }

  .session-menu::backdrop {
    background: rgba(0, 0, 0, 0.4);
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

  .leave-btn {
    margin-top: 1.5rem;
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
