<script lang="ts">
  import { formatCode } from '$lib';

  export let code: string = '';
  export let queued: number = 0;
  export let participants: Array<{ client_id: string; display_name: string; is_host: boolean }> =
    [];
</script>

<article class="session-card">
  <h2>{formatCode(code)}</h2>
  <div class="stats">
    <span class="badge">{queued} track{queued === 1 ? '' : 's'} queued</span>
  </div>
  {#if participants.length}
    <ul class="participants">
      {#each participants as p (p.client_id)}
        <li>{p.display_name}{p.is_host ? ' (host)' : ''}</li>
      {/each}
    </ul>
  {/if}
</article>

<style>
  .session-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .session-card h2 {
    margin: 0 0 0.5rem;
    font-size: 1.1rem;
  }

  .stats {
    margin-top: 0.5rem;
  }

  .badge {
    display: inline-block;
    color: var(--color-text-muted);
    font-size: 0.85rem;
  }

  .participants {
    list-style: none;
    margin: 0.75rem 0 0;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }

  .participants li {
    background: var(--color-surface-muted);
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    font-size: 0.85rem;
  }
</style>
