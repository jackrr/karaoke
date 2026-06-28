<script lang="ts">
  /**
   * Mode: 'timed' | 'raw'.
   * The actual content is managed by the parent store.
   */
  export let mode: 'timed' | 'raw' = 'raw';
</script>

{#if mode === 'timed'}
  <div class="lyrics timed card">
    <div class="lyrics-scrimm">
      <div class="lyric-lines">
        <p class="line"><em>Lyrics will appear here…</em></p>
      </div>
    </div>
  </div>
{:else}
  <div class="lyrics raw card">
    <div class="lyric-scroll">
      <p><em>No lyrics available.</em></p>
    </div>
  </div>
{/if}

<style>
  .lyrics {
    margin: 0;
    flex: 1;
    min-height: 160px;
    overflow: hidden;
  }
  .lyrics.timed {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .lyric-lines {
    text-align: center;
    font-size: 1.1rem;
    line-height: 1.6;
    will-change: transform;
  }
  .line {
    padding: 4px 0;
    transition: color 0.3s, text-shadow 0.3s;
    color: var(--text-secondary);
  }
  .line.active {
    color: var(--text-primary);
    text-shadow: 0 0 12px var(--accent-glow);
    font-weight: 600;
  }
  .lyric-scroll {
    max-height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
    color: var(--text-secondary);
    line-height: 1.8;
  }
  .lyrics-scrimm {
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom,
      var(--bg-card) 0%, transparent 30%, transparent 70%,
      var(--bg-card) 100%);
    pointer-events: none;
  }
</style>
