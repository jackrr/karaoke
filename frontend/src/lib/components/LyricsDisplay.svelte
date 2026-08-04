<script lang="ts">
  import type { LrcLine } from '../utils/lrc';
  import { findCurrentLineIndex } from '../utils/lrc';
  import { fly } from 'svelte/transition';

  let { lines, currentTime }: { lines: LrcLine[]; currentTime: number } = $props();
  const activeIndex = $derived(findCurrentLineIndex(lines, currentTime));
  const activeLine = $derived(activeIndex === -1 ? null : lines[activeIndex]);
  const nextLine = $derived(lines[activeIndex + 1] ?? null);
</script>

<div class="lyrics">
  {#key activeLine?.time ?? 'placeholder'}
    <p
      class="current-line"
      in:fly={{ y: 24, duration: 300 }}
      out:fly={{ y: -24, duration: 300 }}
    >
      {activeLine ? activeLine.text : '♪'}
    </p>
  {/key}
  {#if nextLine}
    {#key nextLine.time}
      <p class="next-line" in:fly={{ y: 24, duration: 300 }}>
        {nextLine.text}
      </p>
    {/key}
  {/if}
</div>

<style>
  .lyrics {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .current-line {
    margin: 0;
    font-size: clamp(1.25rem, 5vw, 2.5rem);
    font-weight: 600;
  }

  .next-line {
    margin: 0.5rem 0 0;
    font-size: clamp(1rem, 4vw, 1.75rem);
    font-weight: 400;
    opacity: 0.4;
  }
</style>
