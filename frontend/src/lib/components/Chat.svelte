<script lang="ts">
  type ChatMessage = { sender: string; text: string; type?: string };

  let { messages, onSend }: { messages: ChatMessage[]; onSend: (text: string) => void } =
    $props();

  let draft = $state('');

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) return;
    onSend(trimmed);
    draft = '';
  }
</script>

<div class="chat">
  {#if messages.length}
    <div class="messages">
      {#each messages as msg}
        <div class="message">
          <strong>{msg.sender}:</strong> {msg.text}
        </div>
      {/each}
    </div>
  {/if}

  <form class="chat-form" onsubmit={handleSubmit}>
    <input class="chat-input" bind:value={draft} placeholder="Type a message..." />
    <button type="submit" class="btn btn-primary">Send</button>
  </form>
</div>

<style>
  .messages {
    max-height: 300px;
    overflow-y: auto;
    margin: 1rem 0;
  }

  .message {
    padding: 0.25rem 0;
    border-bottom: 1px solid #eee;
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

  .btn {
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
