<script lang="ts">
  let { audio, onStop }: { audio: HTMLAudioElement | undefined; onStop: () => void } = $props();

  let playing = $state(false);
  let currentTime = $state(0);
  let duration = $state(0);

  $effect(() => {
    const el = audio;
    if (!el) return;

    const syncPlaying = () => (playing = !el.paused);
    const syncTime = () => (currentTime = el.currentTime);
    const syncDuration = () => (duration = Number.isFinite(el.duration) ? el.duration : 0);

    el.addEventListener('play', syncPlaying);
    el.addEventListener('pause', syncPlaying);
    el.addEventListener('timeupdate', syncTime);
    el.addEventListener('loadedmetadata', syncDuration);

    syncPlaying();
    syncTime();
    syncDuration();

    return () => {
      el.removeEventListener('play', syncPlaying);
      el.removeEventListener('pause', syncPlaying);
      el.removeEventListener('timeupdate', syncTime);
      el.removeEventListener('loadedmetadata', syncDuration);
    };
  });

  function formatTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function togglePlay() {
    if (!audio) return;
    if (audio.paused) audio.play();
    else audio.pause();
  }

  function handleSeek(e: Event) {
    if (!audio) return;
    const value = Number((e.currentTarget as HTMLInputElement).value);
    audio.currentTime = value;
    currentTime = value;
  }

  function handleStop() {
    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }
    onStop();
  }
</script>

<div class="playback-controls">
  <button
    class="play-pause"
    type="button"
    onclick={togglePlay}
    aria-label={playing ? 'Pause' : 'Play'}
  >
    {playing ? '⏸' : '▶'}
  </button>

  <span class="time">{formatTime(currentTime)}</span>

  <input
    class="seek"
    type="range"
    min="0"
    max={duration || 0}
    step="0.1"
    value={currentTime}
    oninput={handleSeek}
    aria-label="Seek"
  />

  <span class="time">{formatTime(duration)}</span>

  <button class="btn btn-secondary stop" type="button" onclick={handleStop}>Stop</button>
</div>

<style>
  .playback-controls {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 600;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem calc(0.75rem + env(safe-area-inset-bottom));
    background: #fff;
    border-top: 1px solid #e2e2e2;
  }

  .play-pause {
    min-width: 44px;
    min-height: 44px;
    border: none;
    border-radius: 50%;
    background: #1a1a1a;
    color: #fff;
    font-size: 1.1rem;
    cursor: pointer;
  }

  .time {
    min-width: 2.75rem;
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: #555;
    font-size: 0.85rem;
  }

  .seek {
    flex: 1;
    min-height: 44px;
  }

  .stop {
    min-height: 44px;
    padding: 0 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
</style>
