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
  import { fly, fade } from 'svelte/transition';

  let {
    sessionId,
    track,
    onStop,
    onEnded,
  }: { sessionId: string; track: Track; onStop: () => void; onEnded?: () => void } = $props();

  function handlePlayStateChange(isPlaying: boolean) {
    updatePlaybackState(sessionId, track.id, isPlaying).catch(() => {
      // Best-effort: a failed sync here shouldn't interrupt local playback.
    });
  }

  const ANNOUNCEMENT_DURATION_MS = 4000;

  let currentTime = $state(0);
  let lines = $state<LrcLine[]>([]);
  let lyricsUnavailable = $state(false);
  let audioEl: HTMLAudioElement | undefined = $state();
  let showAnnouncement = $state(false);

  $effect(() => {
    const trackId = track.id;
    const currentSessionId = sessionId;

    lines = [];
    lyricsUnavailable = false;
    currentTime = 0;
    showAnnouncement = true;

    let cancelled = false;
    const timer = setTimeout(() => {
      if (!cancelled) showAnnouncement = false;
    }, ANNOUNCEMENT_DURATION_MS);

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
      clearTimeout(timer);
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
    onended={onEnded}
  ></audio>

  {#if showAnnouncement}
    {#key track.id}
      <div
        class="track-announcement"
        in:fly={{ y: -16, duration: 300 }}
        out:fade={{ duration: 300 }}
      >
        <p class="announcement-title">{track.title ?? 'Untitled'}</p>
        {#if track.artist}
          <p class="announcement-artist">{track.artist}</p>
        {/if}
      </div>
    {/key}
  {/if}

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
    background: var(--color-bg);
  }

  .track-announcement {
    position: absolute;
    top: calc(1rem + env(safe-area-inset-top));
    left: 50%;
    transform: translateX(-50%);
    z-index: 10;
    text-align: center;
    padding: 0.75rem 1.5rem;
    border-radius: 0.75rem;
    background: var(--color-overlay-surface);
    box-shadow: 0 2px 12px var(--color-shadow);
  }

  .announcement-title {
    margin: 0;
    font-size: 1.1rem;
    font-weight: 700;
  }

  .announcement-artist {
    margin: 0.15rem 0 0;
    font-size: 0.9rem;
    color: var(--color-text-muted);
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
    color: var(--color-text-muted);
    margin: 0;
  }
</style>
