<script lang="ts">
  import { untrack } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import type { Track } from '../api';

  type Participant = { client_id: string; display_name: string };

  let { tracks = [], participants = [], onReorder, onPlay }: {
    tracks: Track[];
    participants: Participant[];
    onReorder: (orderedIds: string[]) => Promise<void>;
    onPlay: (track: Track) => void;
  } = $props();

  let items = $state<Track[]>(untrack(() => [...tracks]));
  let errorMessage = $state('');

  // Bumped every time `items` is replaced, whether by an incoming `tracks`
  // prop update (below) or by our own optimistic reorder (handleFinalize).
  // Svelte 5's `$state` wraps assigned arrays in a new proxy on every write,
  // so comparing an old array reference to the current `items` by `===`
  // does not reliably detect "nothing else changed it since" — a plain
  // version counter does.
  let itemsVersion = 0;

  // Keep the local dnd list in sync whenever the tracks prop changes from
  // outside (e.g. track_added / track_updated / queue_reordered broadcasts).
  $effect(() => {
    items = [...tracks];
    itemsVersion++;
  });

  const STATUS_LABELS: Record<string, string> = {
    pending: 'Pending',
    downloading: 'Downloading',
    fetching_lyrics: 'Fetching lyrics',
    stemming: 'Removing vocals',
    downloaded: 'Downloaded',
    ready: 'Ready',
    error: 'Error',
  };

  function uploaderName(track: Track): string {
    if (track.requested_by_display_name) return track.requested_by_display_name;
    const participant = participants.find((p) => p.client_id === track.requested_by_client_id);
    if (participant) return participant.display_name;
    return track.requested_by_client_id.slice(0, 8);
  }

  function handleConsider(e: CustomEvent<{ items: Track[] }>) {
    items = e.detail.items;
  }

  async function handleFinalize(e: CustomEvent<{ items: Track[] }>) {
    const previousOrder = items;
    const newItems = e.detail.items;
    items = newItems;
    itemsVersion++;
    const optimisticVersion = itemsVersion;
    errorMessage = '';
    try {
      await onReorder(newItems.map((t) => t.id));
    } catch {
      // Only revert if nothing else has replaced `items` since we applied
      // our optimistic update — if a `tracks` prop update (e.g. a
      // queue_reordered broadcast from another member) has already replaced
      // it via the $effect above, reverting here would clobber that newer
      // state with our stale snapshot. Still surface the error to the user
      // either way.
      if (itemsVersion === optimisticVersion) {
        items = previousOrder;
        itemsVersion++;
      }
      errorMessage = 'Failed to reorder the queue. Please try again.';
    }
  }
</script>

<div class="queue-list">
  {#if errorMessage}
    <p class="error">{errorMessage}</p>
  {/if}

  {#if items.length}
    <ul
      class="tracks"
      use:dndzone={{ items, flipDurationMs: 150 }}
      onconsider={handleConsider}
      onfinalize={handleFinalize}
    >
      {#each items as track (track.id)}
        <li class="track">
          <span class="title">{track.title ?? track.source_url ?? track.youtube_video_id}</span>
          <span class="status status-{track.status}">
            {STATUS_LABELS[track.status] ?? track.status}
          </span>
          <span class="uploader">Added by {uploaderName(track)}</span>
          {#if track.status === 'error' && track.error_message}
            <span class="error-message">{track.error_message}</span>
          {/if}
          {#if track.status === 'ready'}
            <button class="btn btn-play" type="button" onclick={() => onPlay(track)}>
              Play
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {:else}
    <p class="empty">No tracks in the queue yet.</p>
  {/if}
</div>

<style>
  .queue-list {
    margin: 1.5rem 0;
  }

  .error {
    color: #d32f2f;
    margin: 0 0 0.5rem;
  }

  .empty {
    color: #666;
  }

  .tracks {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .track {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid #eee;
    cursor: grab;
  }

  .uploader {
    font-size: 0.8rem;
    color: #666;
  }

  .status {
    font-size: 0.85rem;
    color: #666;
  }

  .status-error {
    color: #d32f2f;
  }

  .status-downloaded {
    color: #16a34a;
  }

  .status-ready {
    color: #16a34a;
  }

  .error-message {
    font-size: 0.8rem;
    color: #d32f2f;
  }

  .btn-play {
    padding: 0.2rem 0.75rem;
    font-size: 0.85rem;
  }
</style>
