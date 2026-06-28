<script lang="ts">
  import { writable } from 'svelte/store';
  import { session, connectionState, role } from '$lib/store';
  import PasscodeDisplay from '$lib/components/PasscodeDisplay.svelte';

  let mode = 'create' as 'create' | 'join';
  let joinCode = '';
  let error = '';
  let loading = false;

  async function createRoom() {
    loading = true;
    error = '';
    try {
      const res = await fetch('/api/sessions', { method: 'POST' });
      if (!res.ok) {
        error = 'Failed to create room. Try again.';
        return;
      }
      const { passcode, id } = (await res.json()) as { passcode: string; id: string };
      $session = {
        id,
        passcode,
        status: 'active',
        created_at: Date.now(),
        updated_at: Date.now(),
        expires_at: Date.now() + 3600_000,
      };
      // Host is us — the one who created the room
      $role = 'host';
      connectionState.set('connected');
    } catch {
      error = 'Network error — check your connection.';
    } finally {
      loading = false;
    }
  }

  async function joinRoom() {
    loading = true;
    error = '';
    try {
      const res = await fetch(`/api/sessions/join/${encodeURIComponent(joinCode)}`);
      if (!res.ok) {
        error = 'Room not found';
        return;
      }
      const json = (await res.json()) as { session: typeof $session; role: 'host' | 'guest' };
      $session = json.session;
      $role = json.role;
    } catch {
      error = 'Failed to join — check your connection.';
    } finally {
      loading = false;
    }
  }
</script>

<div class="home">
  <h1 class="title neon-text" id="logo">KARAOKE</h1>
  <p class="subtitle">Pick a mode to get started</p>

  <div class="mode-tabs">
    <button class={`tab ${mode === 'create' ? 'active' : ''}`}
            on:click={() => (mode = 'create')}>
      Create Room
    </button>
    <button class={`tab ${mode === 'join' ? 'active' : ''}`}
            on:click={() => (mode = 'join')}>
      Join Room
    </button>
  </div>

  {#if mode === 'create'}
    <button class="neon-btn large"
            on:click={createRoom}
            disabled={loading}>
      {loading ? 'Creating…' : 'Create Room'}
    </button>
  {:else}
    <form class="join-form" on:submit|default={joinRoom}>
      <input type="text"
             maxlength="6"
             placeholder="Enter 6-digit passcode"
             bind:value={joinCode}
             spellcheck="false"
             autocomplete="off" />
      <button class="neon-btn" type="submit" disabled={loading}>
        {loading ? 'Joining…' : 'Join'}
      </button>
    </form>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if $session && mode === 'create'}
    <PasscodeDisplay passcode={$session.passcode} />
    <div class="room-link">
      <p class="hint">Share this passcode with friends or tap the button to copy</p>
    </div>
  {/if}
</div>

<style>
  .home {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 70vh;
    gap: 20px;
  }
  .title {
    font-size: 2.5rem;
    letter-spacing: 0.15em;
  }
  .subtitle {
    color: var(--text-secondary);
    margin-top: -8px;
  }
  .mode-tabs {
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }
  .tab {
    padding: 10px 28px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.15s;
  }
  .tab.active, .tab:hover {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--text-primary);
  }
  .large { font-size: 1.2rem; padding: 14px 36px; }
  .join-form {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }
  .join-form input {
    padding: 12px 18px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 1.3rem;
    letter-spacing: 0.5em;
    width: 220px;
    text-align: center;
  }
  .join-form input:focus { outline: none; border-color: var(--accent); }
  .error {
    color: var(--error);
    margin-top: 8px;
    font-size: 0.95rem;
  }
  .room-link { margin-top: 8px; }
  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>
