import { expect, test } from '@playwright/test';
import {
  createSessionViaUI,
  createTrackViaApi,
  getClientId,
  waitForWebSocketConnected,
} from '../tests/helpers';

const VIDEO_URLS = [
  'https://www.youtube.com/watch?v=aaaaaaaaaaa',
  'https://www.youtube.com/watch?v=bbbbbbbbbbb',
  'https://www.youtube.com/watch?v=ccccccccccc',
];

type TrackApiResult = { id: string; status: string; title: string | null; position: number };

declare global {
  interface Window {
    __dndFirstItemId?: string;
  }
}

async function fetchTracks(page: import('@playwright/test').Page, sessionId: string) {
  return page.evaluate(
    (sid: string) =>
      fetch(`/sessions/${sid}/tracks`).then((r) => r.json()) as Promise<{
        tracks: TrackApiResult[];
      }>,
    sessionId
  );
}

test.afterEach(async ({ page }) => {
  // Playwright videos aren't finalized until the page/context closes, so
  // close it explicitly here before saving to a fixed, predictable path
  // that CI can find and upload.
  const video = page.video();
  if (video) {
    await page.close();
    await video.saveAs('videos/reorder-dnd.webm');
  }
});

test('drag-and-drop reorders the queue', async ({ page }) => {
  // svelte-dnd-action focuses the dragged clone element while a drag is in
  // progress, and also auto-scrolls the drop zone's scroll container when
  // the cursor nears its edge (SCROLL_ZONE_PX). Either can shift page
  // layout under our fixed set of viewport-relative mouse coordinates
  // mid-gesture and corrupt the drag — e.g. adding the per-row "Play"
  // button was enough extra content to nudge the queue rows within the
  // bottom-edge auto-scroll hot zone, which silently scrolled the page a
  // few pixels and caused the drop to land back in the original slot.
  // Neutralize scrolling for the duration of the test so our precomputed
  // coordinates stay valid throughout the gesture.
  await page.addInitScript(() => {
    Element.prototype.scrollIntoView = () => {};
    Element.prototype.scrollBy = () => {};
    window.scrollBy = () => {};
    const origFocus = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function (this: HTMLElement, opts?: FocusOptions) {
      return origFocus.call(this, { ...(opts ?? {}), preventScroll: true });
    };
  });

  await page.goto('/');
  await createSessionViaUI(page, 'Reorder Video Demo');
  await waitForWebSocketConnected(page);

  const match = page.url().match(/\/session\/([^/?#]+)/);
  if (!match) throw new Error(`Could not extract session id from URL: ${page.url()}`);
  const sessionId = match[1];
  const clientId = await getClientId(page);

  // Seed three distinct tracks via the API. Because SKIP_TRACK_DOWNLOAD=1 is
  // set for this config's webServer, each reaches "ready" almost instantly
  // with placeholder values instead of hitting the real yt-dlp/demucs
  // pipeline.
  const created: string[] = [];
  for (const url of VIDEO_URLS) {
    const track = await createTrackViaApi(page, sessionId, url, clientId);
    created.push(track.id);
  }

  // Wait for all three rows to render and reach the "ready" status.
  const trackRows = page.locator('.track');
  await expect(trackRows).toHaveCount(3);
  await expect(page.locator('.status-ready')).toHaveCount(3, { timeout: 10_000 });

  // Recorded for the video/documentation purposes; the real correctness
  // check below compares track ids from the API, since all seeded tracks
  // share the same placeholder title.
  const initialTitles = await page.locator('.track .title').allTextContents();
  void initialTitles;

  const initialTracks = await fetchTracks(page, sessionId);
  const initialOrder = initialTracks.tracks.map((t) => t.id);
  expect(initialOrder).toEqual(created);
  const draggedTrackId = initialOrder[0];

  // Track the current first-slot item id live from svelte-dnd-action's
  // "consider" events. The library only re-evaluates which slot the
  // dragged item belongs in on a polling interval (derived from
  // flipDurationMs), and near a swap boundary it can flip back and forth a
  // few times before settling — so rather than guessing a fixed hold
  // duration, we drag until we observe the swap actually happen and then
  // release immediately.
  await page.evaluate(() => {
    const zone = document.querySelector('.tracks');
    zone?.addEventListener('consider', (e) => {
      const items = (e as CustomEvent<{ items: Array<{ id: string }> }>).detail.items;
      window.__dndFirstItemId = items[0]?.id;
    });
  });

  // Drag the first row down past the second row. (Dragging all the way to
  // the third row's position pushes the cursor into svelte-dnd-action's
  // bottom-edge auto-scroll hot zone near the bottom of the viewport, which
  // scrolls the page mid-gesture and corrupts our fixed viewport
  // coordinates — so we settle for a one-slot swap, which is still a
  // conclusive proof that DnD reorder works.)
  const firstBox = await trackRows.nth(0).boundingBox();
  const secondBox = await trackRows.nth(1).boundingBox();
  if (!firstBox || !secondBox) throw new Error('Could not read bounding boxes for track rows');

  const startX = firstBox.x + firstBox.width / 2;
  const startY = firstBox.y + firstBox.height / 2;
  const endX = secondBox.x + secondBox.width / 2;
  // Aim deep into the second row's slot (not its exact midpoint) so the
  // swap decision isn't right on the boundary.
  const endY = secondBox.y + secondBox.height * 0.85;

  await page.mouse.move(startX, startY);
  await page.mouse.down();

  // svelte-dnd-action represents the dragged item's current slot with a
  // shadow placeholder element (id "id:dnd-shadow-placeholder-0000") while
  // dragging, so "first item id changed" alone doesn't mean a real swap —
  // it's also true for that placeholder at the very start. Only treat it as
  // swapped once a *different real* track id has taken the first slot.
  const otherTrackIds = new Set(initialOrder.filter((id) => id !== draggedTrackId));
  const steps = 20;
  let swapped = false;
  for (let i = 1; i <= steps && !swapped; i++) {
    const t = i / steps;
    await page.mouse.move(startX + (endX - startX) * t, startY + (endY - startY) * t);
    await page.waitForTimeout(30);
    const firstItemId = await page.evaluate(() => window.__dndFirstItemId);
    if (firstItemId !== undefined && otherTrackIds.has(firstItemId)) {
      swapped = true;
    }
  }

  // Give svelte-dnd-action's flipDurationMs (150ms) settle animation a
  // moment before releasing, then release immediately once swapped so we
  // don't linger at the boundary and risk it flip-flopping back.
  await page.waitForTimeout(200);
  await page.mouse.up();

  // Account for the PUT /sessions/{id}/tracks/order round-trip and
  // queue_reordered broadcast.
  await page.waitForTimeout(300);

  const finalTracks = await fetchTracks(page, sessionId);
  const finalOrder = finalTracks.tracks.map((t) => t.id);

  expect(finalOrder).not.toEqual(initialOrder);
  expect([...finalOrder].sort()).toEqual([...initialOrder].sort());
  // The dragged track (originally first) should no longer be first.
  expect(finalOrder[0]).not.toBe(initialOrder[0]);
});
