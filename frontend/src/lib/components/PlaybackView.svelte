<script lang="ts">
  import { currentTrack } from '$lib/store';

  $: track = $currentTrack;

  function formatTime(s: number) {
    if (!isFinite(s) || s < 0) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  }
</script>

<div class="card playback">
  {@if !track}
    <p style="text-align:center; color: var(--text-muted);">No track playing</p>
  {:else}
    <audio controls class="audio-player" preload="auto">
      <source src="/api/tracks/{track.id}/stream" />
    </audio>
    <div class="progress">
      <span class="time" id="currentTime">0:00</span>
      <progress max={track.duration ?? 0} value={0} class="bar" />
      <span class="time">{formatTime(track.duration ?? 0)}</span>
    </div>
  {/if}
</div>

<style>
  .playback { padding: 12px; }
  .audio-player {
    width: 100%;
    margin-bottom: 8px;
    border-radius: var(--radius-sm);
  }
  .progress {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    color: var(--text-muted);
  }
  .time { width: 32px; text-align: center; font-variant-numeric: tabular-nums; }
  .bar {
    flex: 1;
    height: 4px;
    appearance: none;
    background: var(--bg-tertiary);
    border-radius: 2px;
  }
  .bar::-webkit-progress-bar { background: var(--bg-tertiary); border-radius: 2px; }
  .bar::-webkit-progress-value { background: var(--accent); border-radius: 2px; }
</style>
