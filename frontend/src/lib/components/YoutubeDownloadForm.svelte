<script lang="ts">
  import { DuplicateTrackError, type Track } from '../api';

  let { onSubmit }: {
    onSubmit: (url: string) => Promise<Track>;
  } = $props();

  let url = $state('');
  let submitting = $state(false);
  let errorMessage = $state('');

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
</style>
