<script lang="ts">
  import qrcode from 'qrcode-generator';

  let { value, size = 160 }: { value: string; size?: number } = $props();

  // Type number 0 lets the library pick the smallest size that fits `value`.
  let modules = $derived.by(() => {
    const qr = qrcode(0, 'M');
    qr.addData(value);
    qr.make();
    const count = qr.getModuleCount();
    const cells: boolean[][] = [];
    for (let row = 0; row < count; row++) {
      const line: boolean[] = [];
      for (let col = 0; col < count; col++) {
        line.push(qr.isDark(row, col));
      }
      cells.push(line);
    }
    return cells;
  });

  let cellSize = $derived(modules.length ? size / modules.length : 0);
</script>

<svg
  class="qr-code"
  role="img"
  aria-label="QR code to join session"
  width={size}
  height={size}
  viewBox="0 0 {size} {size}"
>
  <rect width={size} height={size} fill="#fff" />
  {#each modules as row, r (r)}
    {#each row as dark, c (c)}
      {#if dark}
        <rect x={c * cellSize} y={r * cellSize} width={cellSize} height={cellSize} fill="#000" />
      {/if}
    {/each}
  {/each}
</svg>

<style>
  .qr-code {
    display: block;
    background: #fff;
    border: 1px solid #e2e2e2;
    border-radius: 8px;
    padding: 0.5rem;
    box-sizing: content-box;
  }
</style>
