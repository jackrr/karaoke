<script lang="ts">
  import '../app.css';
  import { createSession, listSessions } from '$lib/api';
  import { getDisplayName, setDisplayName } from '$lib/identity';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';

  let loading = $state(false);
  let error = $state<string | null>(null);
  let sessionCount = $state<number | null>(null);
  let displayName = $state(getDisplayName());

  onMount(async () => {
    const redirectError = page.url.searchParams.get('error');
    if (redirectError) {
      error = redirectError;
      await goto('/', { replaceState: true });
    }
    try {
      const data = await listSessions();
      sessionCount = data.count;
    } catch {
      error = error ?? 'Failed to load sessions';
    }
  });

  async function handleCreateSession() {
    if (!displayName.trim()) {
      error = 'Enter a display name';
      return;
    }
    loading = true;
    error = null;
    try {
      const trimmedName = displayName.trim();
      const result = await createSession(trimmedName);
      setDisplayName(trimmedName);
      await goto(`/session/${result.id}`);
    } catch {
      error = 'Failed to create session';
    } finally {
      loading = false;
    }
  }
</script>

<div class="hero">
  <h1>Karaoke</h1>
  <p class="subtitle">Create or join a session to start singing</p>
</div>

{#if error}
  <p class="error">{error}</p>
{/if}

{#if sessionCount !== null}
  <p class="session-count">
    There {sessionCount === 1 ? 'is' : 'are'} currently {sessionCount} active session{sessionCount === 1 ? '' : 's'}.
  </p>
{/if}

<form class="create-form" onsubmit={(e) => { e.preventDefault(); handleCreateSession(); }}>
  <input
    class="display-name-input"
    bind:value={displayName}
    placeholder="Your name"
    aria-label="Display name"
  />
  <button type="submit" class="btn btn-primary" disabled={loading}>
    {loading ? 'Creating...' : 'Create Session'}
  </button>
</form>

<p class="join-link">Have a code? <a href="/join">Join a session</a> — ask the host for their 6-digit session code.</p>

<style>
  .hero {
    text-align: center;
    padding: 4rem 0;
  }

  .hero h1 {
    margin: 0;
    font-size: 3rem;
  }

  .subtitle {
    color: #666;
    margin-top: 0.5rem;
  }

  .btn {
    display: inline-block;
    padding: 0.6rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
    transition: opacity 0.15s;
  }

  .btn-primary {
    background: #4a90d9;
    color: #fff;
  }

  .btn:hover {
    opacity: 0.85;
  }

  .error {
    color: #d32f2f;
    margin: 1rem;
  }

  .session-count {
    text-align: center;
    color: #666;
    margin: 1rem;
  }

  .create-form {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    align-items: center;
  }

  .display-name-input {
    padding: 0.6rem 0.75rem;
    border: 1px solid #ccc;
    border-radius: 6px;
    font-size: 1rem;
  }

  .join-link {
    text-align: center;
    margin-top: 1rem;
  }

  .join-link a {
    color: #4a90d9;
  }
</style>
