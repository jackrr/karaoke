<script lang="ts">
  import { DuplicateTrackError, type Track } from '../api';

  let { tracks = [], onSubmit, onPlay }: {
    tracks: Track[];
    onSubmit: (url: string) => Promise<Track>;
    onPlay: (track: Track) => void;
  } = $props();

  let url = $state('');
  let submitting = $state(false);
  let errorMessage = $state('');

  const STATUS_LABELS: Record<string, string> = {
    pending: 'Pending',
    downloading: 'Downloading',
    fetching_lyrics: 'Fetching lyrics',
    stemming: 'Removing vocals',
    downloaded: 'Downloaded',
    ready: 'Ready',
    error: 'Error',
  };

  async function handleSubmit() {
    if (!url.trim() || submitting) return;
    submitting = true;
    errorMessage = '';
    try {
      await onSubmit(url.trim());
      url = '';
    } catch (err) {
      if (err instanceof DuplicateTrackError) {
        errorMessage = 'This video has already been added to the session.';
      } else {
        errorMessage = 'Failed to add track. Please try again.';
      }
    } finally {
      submitting = false;
    }
  }
</script>

<div class="youtube-download-form">
  <form
    onsubmit={(e) => {
      e.preventDefault();
      handleSubmit();
    }}
  >
    <input
      class="url-input"
      type="text"
      bind:value={url}
      placeholder="Paste a YouTube URL..."
      disabled={submitting}
    />
    <button class="btn btn-primary" type="submit" disabled={submitting || !url.trim()}>
      {submitting ? 'Adding...' : 'Add Track'}
    </button>
  </form>

  {#if errorMessage}
    <p class="error">{errorMessage}</p>
  {/if}

  {#if tracks.length}
    <ul class="tracks">
      {#each tracks as track (track.id)}
        <li class="track">
          <span class="title">{track.title ?? track.youtube_video_id}</span>
          <span class="status status-{track.status}">
            {STATUS_LABELS[track.status] ?? track.status}
          </span>
          {#if track.status === 'error' && track.error_message}
            <span class="error-message">{track.error_message}</span>
          {/if}
          {#if track.status === 'downloaded'}
            <button class="btn btn-play" type="button" onclick={() => onPlay(track)}>
              Play
            </button>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .youtube-download-form {
    margin: 1.5rem 0;
  }

  form {
    display: flex;
    gap: 1rem;
  }

  .url-input {
    flex: 1;
    padding: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .error {
    color: #d32f2f;
    margin: 0.5rem 0 0;
  }

  .tracks {
    list-style: none;
    margin: 1rem 0 0;
    padding: 0;
  }

  .track {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    padding: 0.4rem 0;
    border-bottom: 1px solid #eee;
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
