<script lang="ts">
  import { capitalize } from '$lib/utils/string';
  import { getSession, leaveSession, createSessionWebSocket } from '$lib/api';
  import { goto } from '$app/navigation';
  import { onMount, onDestroy } from 'svelte';

  let session = $state<{ name: string; online: number } | null>(null);
  let loading = $state(true);
  let connected = $state(false);
  let message = $state('');
  let messages = $state<Array<{ sender: string; text: string; type?: string }>>([]);
  let ws: ReturnType<typeof createSessionWebSocket> | null = null;
  let sessionId = '';

  onMount(async () => {
    sessionId = new URL(window.location.href).pathname.replace('/session/', '');
    const data = await getSession(sessionId);
    if (!data) {
      loading = false;
      return;
    }
    session = data;
    loading = false;

    ws = createSessionWebSocket(sessionId, {
      onOpen: () => {
        connected = true;
      },
      onClose: () => {
        connected = false;
      },
      onMessage: (msg) => {
        const typed = msg as { type: string; data: { text: string; sender: string } };
        if (typed.type === 'message' && typed.data?.text) {
          messages.push({ sender: typed.data.sender ?? 'unknown', text: typed.data.text, type: typed.type });
        }
      },
    });
  });

  onDestroy(() => {
    ws?.close();
  });

  async function handleLeave() {
    await leaveSession(sessionId);
    goto('/');
  }

  function handleSend() {
    if (!ws || !message.trim()) return;
    // The server broadcasts to every connection in the session, including the
    // sender's own socket — `onMessage` renders it, so don't also push here.
    ws.send('message', { text: message.trim(), sender: 'you' });
    message = '';
  }
</script>

{#if session}
  <h1>{capitalize(session.name)}</h1>
  <p class="online">{session.online} online</p>

  <p class="status" class:connected>{connected ? 'Connected' : 'Disconnected'}</p>

  {#if messages.length}
    <div class="messages">
      {#each messages as msg}
        <div class="message">
          <strong>{msg.sender}:</strong> {msg.text}
        </div>
      {/each}
    </div>
  {/if}

  <form class="chat-form" onsubmit={(e) => { e.preventDefault(); handleSend(); }}>
    <input class="chat-input" bind:value={message} placeholder="Type a message..." />
    <button type="submit" class="btn btn-primary">Send</button>
  </form>

  <button class="btn btn-secondary" onclick={handleLeave}>Leave Session</button>
{:else if loading}
  <p class="loading">Loading session...</p>
{/if}

<style>
  h1 { font-size: 2rem; }

  .online { color: #666; }

  .connected { color: #16a34a; }
  .status:not(.connected) { color: #d32f2f; }

  .messages {
    max-height: 300px;
    overflow-y: auto;
    margin: 1rem 0;
  }

  .message {
    padding: 0.25rem 0;
    border-bottom: 1px solid #eee;
  }

  form {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
  }

  input {
    flex: 1;
    padding: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .loading {
    margin: 1rem;
  }
  
  .chat-form {
    display: flex;
    gap: 1rem;
    margin: 1.5rem 0;
  }

  .chat-input {
    flex: 1;
    padding: 0.5rem;
  }
</style>
