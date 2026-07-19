export type LrcLine = { time: number; text: string };

export function parseLrc(content: string): LrcLine[] {
  const lineRe = /^\[(\d+):(\d+(?:\.\d+)?)\](.*)$/;
  const lines: LrcLine[] = [];
  for (const raw of content.split(/\r?\n/)) {
    const match = raw.match(lineRe);
    if (!match) continue;
    const minutes = Number(match[1]);
    const seconds = Number(match[2]);
    const text = match[3].trim();
    if (!text) continue;
    lines.push({ time: minutes * 60 + seconds, text });
  }
  return lines.sort((a, b) => a.time - b.time);
}

export function findCurrentLineIndex(
  lines: LrcLine[],
  currentTime: number,
): number {
  let idx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].time <= currentTime) idx = i;
    else break;
  }
  return idx;
}
