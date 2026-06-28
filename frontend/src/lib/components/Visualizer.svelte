<script lang="ts">
  import { currentTrack, lyrics } from '$lib/store';
  import { onMount, onDestroy } from 'svelte';

  export let canvasId: string = 'visualizer-canvas';

  let canvas: HTMLCanvasElement;
  let animFrame: number;
  let analyser: AnalyserNode;
  let dataArray: Uint8Array;
  let audioCtx: AudioContext | null = null;

  $: track = $currentTrack;
  $: isTimed = $lyrics?.isTimed ?? false;

  function initAudio() {
    if (!audioCtx) {
      audioCtx = new AudioContext();
      // Connect the page's audio output to the analyser
      const dest = audioCtx.createMediaStreamDestination();
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      dataArray = new Uint8Array(analyser.frequencyBinCount);
    }
  }

  function draw() {
    if (!analyser || !canvas) return;
    animFrame = requestAnimationFrame(draw);
    analyser.getByteFrequencyData(dataArray);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const width = canvas.width;
    const height = canvas.height;

    ctx.fillStyle = '#0a0a0f';
    ctx.fillRect(0, 0, width, height);

    const barWidth = (width / dataArray.length) * 2.5;
    let x = 0;
    for (let i = 0; i < dataArray.length; i++) {
      const barHeight = (dataArray[i] / 255) * height;
      const hue = (i / dataArray.length) * 60 + 340; // pink-red range
      ctx.fillStyle = `hsl(${hue}, 80%, 60%)`;
      ctx.fillRect(x, height - barHeight, barWidth, barHeight);
      x += barWidth + 1;
    }
  }

  onMount(() => {
    initAudio();
    draw();
  });

  onDestroy(() => {
    cancelAnimationFrame(animFrame);
    if (audioCtx) audioCtx.close();
  });
</script>

<canvas bind:this={canvas} id={canvasId} width={300} height={120} class="visualizer-canvas" />

<style>
  .visualizer-canvas {
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background: var(--bg-secondary);
  }
</style>
