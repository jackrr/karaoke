<script lang="ts">
  import {
    getTrackAudioUrl,
    fetchTrackLyrics,
    LyricsNotAvailableError,
    updatePlaybackState,
    type Track,
  } from '../api';
  import { parseLrc, type LrcLine } from '../utils/lrc';
  import LyricsDisplay from './LyricsDisplay.svelte';
  import PlaybackControls from './PlaybackControls.svelte';

  let { sessionId, track, onStop }: { sessionId: string; track: Track; onStop: () => void } =
    $props();

  function handlePlayStateChange(isPlaying: boolean) {
    updatePlaybackState(sessionId, track.id, isPlaying).catch(() => {
      // Best-effort: a failed sync here shouldn't interrupt local playback.
    });
  }

  let currentTime = $state(0);
  let lines = $state<LrcLine[]>([]);
  let lyricsUnavailable = $state(false);
  let audioEl: HTMLAudioElement | undefined = $state();

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
    bind:this={audioEl}
    preload="metadata"
    bind:currentTime
    src={getTrackAudioUrl(sessionId, track.id)}
    style="display:none"
  ></audio>

  <div class="lyrics-area">
    {#if lyricsUnavailable}
      <p class="no-lyrics">No lyrics available for this track.</p>
    {:else}
      <LyricsDisplay {lines} {currentTime} />
    {/if}
  </div>

  <PlaybackControls audio={audioEl} {onStop} onPlayStateChange={handlePlayStateChange} />
</div>

<style>
  .track-player {
    position: fixed;
    inset: 0;
    z-index: 500;
    display: flex;
    background: #fafafa;
  }

  .lyrics-area {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: calc(4rem + env(safe-area-inset-top)) 1.5rem calc(5rem + env(safe-area-inset-bottom));
    text-align: center;
  }

  .no-lyrics {
    color: #666;
    margin: 0;
  }
</style>
