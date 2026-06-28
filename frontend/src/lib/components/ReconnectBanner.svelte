<script lang="ts">
  type State = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'disconnected';
  export let connectionState: State = 'idle';

  const messageMap: Record<State, string> = {
    idle:           '',
    connecting:     'Connecting…',
    connected:      '',
    reconnecting:   'Reconnecting… (attempt <attempt>/5)',
    disconnected:   'Connection lost — tap to retry',
  };

  $: msg = messageMap[connectionState];
  $: visible = msg !== '';
</script>

{#if visible}
  <div class={`reconnect-banner banner ${connectionState}`}
       role="alert"
       on:click={() => connectionState === 'disconnected' && (msg = 'reconnecting')}>
    <span class="dot" />
    <span>{msg}</span>
  </div>
{/if}

<style>
  .reconnect-banner {
    position: fixed;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 24px;
    border-radius: 0 0 12px 12px;
    font-size: 0.85rem;
    z-index: 100;
    white-space: nowrap;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-top: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  }
  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    animation: pulse 1.2s infinite;
  }
  .connected .dot { background: var(--success); animation: none; }
  .disconnected { cursor: pointer; }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.3; }
  }
</style>
