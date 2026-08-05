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
