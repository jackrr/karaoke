<script lang="ts">
  import '../app.css';
  import { createSession, listSessions } from '$lib/api';
  import { capitalize } from '$lib/utils/string';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';

  let loading = $state(false);
  let error = $state<string | null>(null);
  let sessions = $state<{ id: string; name: string }[]>([]);

  onMount(async () => {
    try {
      const data = await listSessions();
      sessions = data.sessions;
    } catch {
      error = 'Failed to load sessions';
    }
  });

  async function handleCreateSession() {
    loading = true;
    error = null;
    try {
      const result = await createSession('My Session');
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

{#if loading}
  <p class="loading">Loading sessions...</p>
{/if}

{#if sessions.length}
  <div class="session-list">
    {#each sessions as s}
      <button
        class="btn btn-secondary"
        onclick={() => goto(`/session/${s.id}`)}
      >
        {capitalize(s.name)}
      </button>
    {/each}
  </div>
{/if}

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

  .btn-secondary {
    background: #e2e2e2;
    color: #1a1a1a;
  }

  .btn:hover {
    opacity: 0.85;
  }

  .error {
    color: #d32f2f;
    margin: 1rem;
  }

  .loading {
    margin: 1rem;
  }

  .session-list {
    display: flex;
    gap: 1rem;
    justify-content: center;
    padding: 2rem;
  }
</style>
