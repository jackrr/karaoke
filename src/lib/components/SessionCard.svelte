<script lang="ts">
  import { capitalize, formatPasscode } from '$lib';

  export let title: string = '';
  export let passcode: string = '';
  export let host: string = '';
  export let queued: number = 0;
</script>

<article class="session-card">
  <h2>{capitalize(title)}</h2>
  <p>Passcode: <code>{formatPasscode(passcode)}</code></p>
  {#if host}
    <p class="host">Host: <kbd>{host}</kbd></p>
  {/if}
  <div class="stats">
    <span class="badge">{queued} track{queued === 1 ? '' : 's'} queued</span>
  </div>
</article>

<style>
  .session-card {
    background: #fff;
    border: 1px solid #e2e2e2;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .session-card h2 {
    margin: 0 0 0.5rem;
    font-size: 1.1rem;
  }

  .session-card p {
    margin: 0.25rem 0;
  }

  code {
    font-family: ui-monospace, monospace;
    background: #f0f0f0;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  .host {
    color: #666;
    font-size: 0.9rem;
  }

  .stats {
    margin-top: 0.5rem;
  }

  .badge {
    display: inline-block;
    color: #555;
    font-size: 0.85rem;
  }
</style>
