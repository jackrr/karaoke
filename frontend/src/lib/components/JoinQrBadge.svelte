<script lang="ts">
  import QrCode from './QrCode.svelte';
  import { formatCode } from '../utils/string';

  let { joinUrl, code }: { joinUrl: string; code: string } = $props();
</script>

<div class="join-card">
  <p class="caption">Scan to join</p>
  <QrCode value={joinUrl} size={120} />
  <p class="code">{formatCode(code)}</p>
</div>

<style>
  .join-card {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    z-index: 20;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    box-shadow: 0 4px 16px var(--color-shadow);
    padding: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }

  .caption {
    margin: 0;
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }

  .code {
    margin: 0;
    font-family: ui-monospace, monospace;
    font-size: 1rem;
    color: var(--color-text);
  }
</style>
