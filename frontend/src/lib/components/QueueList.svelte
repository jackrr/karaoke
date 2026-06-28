<script lang="ts">
  import type { QueueEntry } from '$lib/store';

  export let items: QueueEntry[] = [];
  export let isHost: boolean = false;

  function sourceIcon(src: string) {
    return src === 'youtube' ? '🎬' : src === 'upload' ? '📁' : '📺';
  }
</script>

<div class="queue card">
  {@if items.length === 0}
    <p class="empty">No tracks in the queue yet.</p>
  {:else}
    <div class="list">
      {#each items as entry (entry.id)}
        <div class={`queue-item ${entry.status}`}>
          {#if isHost}
            <span class="drag-handle">⋮⋮</span>
          {/if}
          <span class="pos">{entry.position}</span>
          <span class="icon">{sourceIcon(entry.source)}</span>
          <span class="meta">
            <strong>{entry.metadata?.title ?? entry.metadata?.name ?? 'Untitled'}</strong>
            {#if entry.metadata?.artist}
              <small> — {entry.metadata.artist}</small>
            {/if}
          </span>
          <span class={`badge status-badge {entry.status}`}>
            {entry.status}
          </span>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .queue { padding: 0; }
  .empty {
    text-align: center;
    color: var(--text-muted);
    margin: 32px 0;
  }
  .list { display: flex; flex-direction: column; gap: 4px; }
  .queue-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    transition: background 0.15s;
  }
  .queue-item:hover { background: var(--bg-tertiary); }
  .drag-handle {
    color: var(--text-muted);
    cursor: grab;
    font-size: 1.2rem;
  }
  .pos {
    width: 24px;
    text-align: right;
    color: var(--text-muted);
    font-size: 0.85rem;
    font-variant-numeric: tabular-nums;
  }
  .icon { font-size: 1.2rem; }
  .meta { flex: 1; font-size: 0.95rem; }
  .meta small { color: var(--text-secondary); }
  .badge {
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 999px;
    text-transform: uppercase;
    font-weight: 600;
  }
  .status-badge.pending    { background: var(--bg-tertiary); color: var(--text-muted); }
  .status-badge.processing { background: var(--warning)40; color: var(--warning); }
  .status-badge.ready      { background: var(--success)40; color: var(--success); }
  .status-badge.error      { background: var(--error)40; color: var(--error); }
</style>
