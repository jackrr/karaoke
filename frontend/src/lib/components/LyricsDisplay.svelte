<script lang="ts">
  import type { LrcLine } from '../utils/lrc';
  import { findCurrentLineIndex } from '../utils/lrc';

  let { lines, currentTime }: { lines: LrcLine[]; currentTime: number } = $props();
  const activeIndex = $derived(findCurrentLineIndex(lines, currentTime));
</script>

<div class="lyrics">
  {#each lines as line, i (line.time)}
    <p class:active={i === activeIndex}>{line.text}</p>
  {/each}
</div>

<style>
  .lyrics p {
    opacity: 0.5;
    transition: opacity 0.2s;
  }

  .lyrics p.active {
    opacity: 1;
    font-weight: 600;
  }
</style>
