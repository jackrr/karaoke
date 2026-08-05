<script lang="ts">
  import { untrack } from 'svelte';

  let { vocalVolumeFraction, onUpdate }: {
    vocalVolumeFraction: number;
    onUpdate: (value: number) => Promise<void>;
  } = $props();

  let value = $state(untrack(() => vocalVolumeFraction));
  let submitting = $state(false);
  let errorMessage = $state('');

  // Reflect external updates (e.g. a websocket broadcast from another
  // client) unless the user has an unsaved edit in progress, or a failed
  // save left an edit the error message is asking them to retry.
  $effect(() => {
    if (!submitting && !errorMessage) value = vocalVolumeFraction;
  });

  async function handleSave() {
    if (submitting) return;
    submitting = true;
    errorMessage = '';
    try {
      await onUpdate(value);
    } catch {
      errorMessage = 'Failed to save. Please try again.';
    } finally {
      submitting = false;
    }
  }
</script>

<div class="session-settings">
  <label for="vocal-gain">
    Background vocal gain: {value.toFixed(2)}
  </label>
  <div class="gain-row">
    <input
      id="vocal-gain"
      type="range"
      min="0"
      max="1"
      step="0.01"
      bind:value
      disabled={submitting}
    />
    <button class="btn btn-primary" type="button" onclick={handleSave} disabled={submitting}>
      {submitting ? 'Saving...' : 'Save'}
    </button>
  </div>

  {#if errorMessage}
    <p class="error">{errorMessage}</p>
  {/if}
</div>

<style>
  .session-settings {
    margin: 1.5rem 0;
  }

  .gain-row {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  input[type='range'] {
    flex: 1;
  }

  .btn {
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-primary {
    background: var(--color-accent);
    color: var(--color-accent-text);
  }

  .btn:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .error {
    color: var(--color-error);
    margin: 0.5rem 0 0;
  }
</style>
