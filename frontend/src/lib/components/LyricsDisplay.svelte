<script lang="ts">
  import type { LrcLine } from '../utils/lrc';
  import { findCurrentLineIndex } from '../utils/lrc';

  let { lines, currentTime }: { lines: LrcLine[]; currentTime: number } = $props();
  const activeIndex = $derived(findCurrentLineIndex(lines, currentTime));
  const activeLine = $derived(activeIndex === -1 ? null : lines[activeIndex]);
</script>

<div class="lyrics">
  <p class="current-line">{activeLine ? activeLine.text : '♪'}</p>
</div>

<style>
  .lyrics {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
  }

  .current-line {
    margin: 0;
    font-size: clamp(1.25rem, 5vw, 2.5rem);
    font-weight: 600;
  }
</style>
