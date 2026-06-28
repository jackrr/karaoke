<script lang="ts">
  interface Props {
    onEnqueue: (url: string, source: 'youtube' | 'upload') => void;
  }
  export let onEnqueue: Props['onEnqueue'];

  let url = '';
  let source: 'youtube' | 'upload' = 'youtube';

  function handleAdd() {
    if (!url.trim()) return;
    onEnqueue(url, source);
    url = '';
  }
</script>

<div class="enqueue-menu card">
  <h3>Enqueue a Track</h3>
  <div class="row">
    <button class={`pill ${source === 'youtube' ? 'active' : ''}`}
            on:click={() => (source = 'youtube')}>
      🎬 YouTube
    </button>
    <button class={`pill ${source === 'upload' ? 'active' : ''}`}
            on:click={() => (source = 'upload')}>
      📁 Upload
    </button>
  </div>
  <input type="text"
         placeholder={source === 'youtube' ? 'Paste YouTube URL…' : 'Paste file path…'}
         bind:value={url}
         on:keydown={(e) => e.key === 'Enter' && handleAdd()} />
  <button class="neon-btn" on:click={handleAdd}>Enqueue</button>
</div>

<style>
  .enqueue-menu { display: flex; flex-direction: column; gap: 12px; }
  .row { display: flex; gap: 8px; }
  .pill {
    padding: 6px 16px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;
  }
  .pill.active {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--text-primary);
  }
  input {
    width: 100%;
    padding: 10px 14px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: 0.95rem;
  }
  input:focus { outline: none; border-color: var(--accent); }
</style>
