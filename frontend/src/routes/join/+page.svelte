<script lang="ts">
  import { joinSession } from '$lib/api';
  import { getDisplayName, setDisplayName } from '$lib/identity';
  import { formatCode } from '$lib/utils/string';
  import { goto } from '$app/navigation';

  let code = $state('');
  let displayName = $state(getDisplayName());
  let loading = $state(false);
  let error = $state<string | null>(null);

  function handleCodeInput(e: Event) {
    // Strip anything pasted or typed that isn't a digit (spaces, dashes,
    // etc.) so the join code is always clean regardless of how it arrived.
    code = (e.currentTarget as HTMLInputElement).value.replace(/\D/g, '').slice(0, 6);
  }

  async function handleJoin() {
    if (code.length !== 6) {
      error = 'Enter the 6-digit session code';
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
      const result = await joinSession(code, trimmedName);
      setDisplayName(trimmedName);
      await goto(`/session/${result.id}`);
    } catch {
      error = 'Failed to join session — check the session code and try again';
    } finally {
      loading = false;
    }
  }
</script>

<div class="hero">
  <h1>Join a session</h1>
  <p class="subtitle">Enter the 6-digit session code to join</p>
</div>

{#if error}
  <p class="error">{error}</p>
{/if}

<form class="join-form" onsubmit={(e) => { e.preventDefault(); handleJoin(); }}>
  <input
    class="code-input"
    value={code}
    oninput={handleCodeInput}
    placeholder="123456"
    inputmode="numeric"
    aria-label="Session code"
  />
  <p class="code-preview">{formatCode(code)}</p>
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
    color: var(--color-text-muted);
    margin-top: 0.5rem;
  }

  .join-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    max-width: 320px;
    margin: 0 auto;
  }

  .code-input,
  .display-name-input {
    padding: 0.6rem 0.75rem;
    border: 1px solid var(--color-input-border);
    border-radius: 6px;
    font-size: 1rem;
  }

  .code-preview {
    text-align: center;
    font-family: ui-monospace, monospace;
    color: var(--color-text-muted);
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
    background: var(--color-accent);
    color: var(--color-accent-text);
  }

  .error {
    color: var(--color-error);
    margin: 1rem;
    text-align: center;
  }

  .back-link {
    text-align: center;
    margin-top: 1.5rem;
  }

  .back-link a {
    color: var(--color-text);
    text-decoration: none;
  }
</style>
