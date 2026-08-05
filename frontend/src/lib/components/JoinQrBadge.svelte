<script lang="ts">
  import QrCode from './QrCode.svelte';
  import { formatCode } from '../utils/string';

  let { joinUrl, code }: { joinUrl: string; code: string } = $props();

  let open = $state(false);
</script>

{#if open}
  <div class="join-card">
    <button class="close-btn" type="button" onclick={() => (open = false)} aria-label="Close QR code">
      ✕
    </button>
    <p class="caption">Scan to join</p>
    <QrCode value={joinUrl} />
    <p class="code">{formatCode(code)}</p>
  </div>
{:else}
  <button class="toggle-btn" type="button" onclick={() => (open = true)} aria-label="Show QR code to join">
    Join
  </button>
{/if}

<style>
  .toggle-btn {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    z-index: 20;
    padding: 0.6rem 1rem;
    background: #4a90d9;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.9rem;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }

  .join-card {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    z-index: 20;
    background: #fff;
    border: 1px solid #e2e2e2;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .close-btn {
    position: absolute;
    top: 0.4rem;
    right: 0.4rem;
    min-width: 32px;
    min-height: 32px;
    border: none;
    background: transparent;
    font-size: 1rem;
    cursor: pointer;
  }

  .caption {
    margin: 0;
    font-size: 0.85rem;
    color: #555;
  }

  .code {
    margin: 0;
    font-family: ui-monospace, monospace;
    font-size: 1rem;
    color: #333;
  }
</style>
