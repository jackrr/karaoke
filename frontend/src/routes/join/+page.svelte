<script lang="ts">
  import '../../app.css';
  import { joinSession } from '$lib/api';
  import { getDisplayName, setDisplayName } from '$lib/identity';
  import { formatPasscode } from '$lib/utils/string';
  import { goto } from '$app/navigation';

  let passcode = $state('');
  let displayName = $state(getDisplayName());
  let loading = $state(false);
  let error = $state<string | null>(null);

  async function handleJoin() {
    const digits = passcode.replace(/\D/g, '');
    if (digits.length !== 6) {
      error = 'Enter the 6-digit passcode';
      return;
    }
    if (!displayName.trim()) {
      error = 'Enter a display name';
      return;
    }
    loading = true;
    error = null;
    try {
      const trimmedName = displayName.trim();
      const result = await joinSession(digits, trimmedName);
      setDisplayName(trimmedName);
      await goto(`/session/${result.id}`);
    } catch {
      error = 'Failed to join session — check the passcode and try again';
    } finally {
      loading = false;
    }
  }
</script>

<div class="hero">
  <h1>Join a session</h1>
  <p class="subtitle">Enter the 6-digit passcode to join</p>
</div>

{#if error}
  <p class="error">{error}</p>
{/if}

<form class="join-form" onsubmit={(e) => { e.preventDefault(); handleJoin(); }}>
  <input
    class="passcode-input"
    bind:value={passcode}
    placeholder="123456"
    inputmode="numeric"
    maxlength="6"
    aria-label="Passcode"
  />
  <p class="passcode-preview">{formatPasscode(passcode.replace(/\D/g, ''))}</p>
  <input
    class="display-name-input"
    bind:value={displayName}
    placeholder="Your name"
    aria-label="Display name"
  />
  <button type="submit" class="btn btn-primary" disabled={loading}>
    {loading ? 'Joining...' : 'Join Session'}
  </button>
</form>

<p class="back-link"><a href="/">← Back home</a></p>

<style>
  .hero {
    text-align: center;
    padding: 4rem 0 2rem;
  }

  .hero h1 {
    margin: 0;
    font-size: 2.5rem;
  }

  .subtitle {
    color: #666;
    margin-top: 0.5rem;
  }

  .join-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-width: 320px;
    margin: 0 auto;
  }

  .passcode-input,
  .display-name-input {
    padding: 0.6rem 0.75rem;
    border: 1px solid #ccc;
    border-radius: 6px;
    font-size: 1rem;
  }

  .passcode-preview {
    text-align: center;
    font-family: ui-monospace, monospace;
    color: #666;
    margin: 0;
  }

  .btn {
    display: inline-block;
    padding: 0.6rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    cursor: pointer;
  }

  .btn-primary {
    background: #4a90d9;
    color: #fff;
  }

  .error {
    color: #d32f2f;
    margin: 1rem;
    text-align: center;
  }

  .back-link {
    text-align: center;
    margin-top: 1.5rem;
  }

  .back-link a {
    color: #333;
    text-decoration: none;
  }
</style>
