<script lang="ts">
  interface Props {
    passcode: string;
  }
  export let passcode: Props['passcode'];

  let copied = false;

  async function copy() {
    try {
      await navigator.clipboard.writeText(passcode);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  }
</script>

<div class="passcode-card card">
  <h2 class="neon-text">Room Passcode</h2>
  <div class="passcode">
    {@html passcode.split('').map(c => `<span class='digit'>{c}</span>`).join('')}
  </div>
  <button class="copy-btn" on:click={copy}>
    {copied ? 'Copied!' : 'Copy'}
  </button>
</div>

<style>
  .passcode-card {
    text-align: center;
    margin: 24px auto;
    max-width: 320px;
  }
  .passcode {
    font-size: 3rem;
    letter-spacing: 0.5em;
    font-weight: 700;
    margin: 16px 0;
    color: var(--accent);
    text-shadow: 0 0 20px var(--accent-glow);
  }
  .digit {
    display: inline-block;
    animation: pop 0.2s ease-out both;
  }
  .copy-btn {
    background: transparent;
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 8px 20px;
    border-radius: var(--radius);
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }
  .copy-btn:hover {
    background: var(--accent);
    color: var(--text-primary);
  }
  @keyframes pop {
    from { transform: scale(0.5); opacity: 0; }
    to   { transform: scale(1);   opacity: 1; }
  }
</style>
