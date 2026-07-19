<script lang="ts">
  import { getTrackAudioUrl, fetchTrackLyrics, LyricsNotAvailableError, type Track } from '../api';
  import { parseLrc, type LrcLine } from '../utils/lrc';
  import LyricsDisplay from './LyricsDisplay.svelte';

  let { sessionId, track }: { sessionId: string; track: Track } = $props();

  let currentTime = $state(0);
  let lines = $state<LrcLine[]>([]);
  let lyricsUnavailable = $state(false);

  $effect(() => {
    const trackId = track.id;
    const currentSessionId = sessionId;

    lines = [];
    lyricsUnavailable = false;
    currentTime = 0;

    let cancelled = false;

    (async () => {
      try {
        const text = await fetchTrackLyrics(currentSessionId, trackId);
        if (cancelled) return;
        lines = parseLrc(text);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof LyricsNotAvailableError) lyricsUnavailable = true;
      }
    })();

    return () => {
      cancelled = true;
    };
  });
</script>

<div class="track-player">
  <audio
    controls
    preload="metadata"
    bind:currentTime
    src={getTrackAudioUrl(sessionId, track.id)}
  ></audio>

  {#if lyricsUnavailable}
    <p class="no-lyrics">No lyrics available for this track.</p>
  {:else}
    <LyricsDisplay {lines} {currentTime} />
  {/if}
</div>

<style>
  .track-player {
    margin: 1.5rem 0;
  }

  audio {
    width: 100%;
  }

  .no-lyrics {
    color: #666;
    margin: 1rem 0 0;
  }
</style>
