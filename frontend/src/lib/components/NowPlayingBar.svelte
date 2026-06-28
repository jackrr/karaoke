<script lang="ts">
  import { currentTrack, lyrics } from '$lib/store';
  import LyricDisplay from './LyricDisplay.svelte';

  $: track = $currentTrack;
  $: lyricsType = $lyrics.type;
</script>

{#if track}
  <div class="now-playing card">
    <div class="track-info">
      <h3 class="neon-text">{track.title}</h3>
      {#if track.artist}
        <p class="artist">{track.artist}</p>
      {/if}
    </div>
    <div class="lyric-section">
      <LyricDisplay {lyricsType} />
    </div>
  </div>
{/if}

<style>
  .now-playing {
    margin-bottom: 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    align-items: flex-start;
  }
  .track-info { flex: 1; min-width: 200px; }
  .track-info h3 { font-size: 1.2rem; }
  .track-info .artist {
    color: var(--text-secondary);
    font-size: 0.95rem;
    margin-top: 4px;
  }
  .lyric-section {
    flex: 1 1 300px;
    min-height: 160px;
  }
</style>
