import asyncio
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .database import get_db
from .websocket_manager import manager

logger = logging.getLogger(__name__)


async def _touch_active_connections(db) -> None:
    """Refresh `last_active_at` for every session that currently has at
    least one live websocket connection.

    This is the "heartbeat via sweep" design: rather than a per-connection
    timer, every sweep iteration simply touches whichever sessions the
    connection manager currently considers active, so any session with a
    connected client is refreshed each interval even with zero other
    activity.
    """
    session_ids = list(manager.active.keys())
    if not session_ids:
        return
    await db.executemany(
        "UPDATE sessions SET last_active_at = CURRENT_TIMESTAMP WHERE id = ?",
        [(sid,) for sid in session_ids],
    )
    await db.commit()


async def reap_expired_sessions(storage_dir: str, ttl_seconds: float) -> int:
    """Delete sessions (and their tracks/members/storage) whose
    `last_active_at` is older than `ttl_seconds` ago. Returns the count of
    sessions reaped."""
    db = await get_db()
    cutoff = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=ttl_seconds)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    async with db.execute(
        "SELECT id FROM sessions WHERE last_active_at < ?", (cutoff,)
    ) as cursor:
        rows = await cursor.fetchall()
    session_ids = [row[0] for row in rows]
    if not session_ids:
        return 0

    placeholders = ",".join("?" * len(session_ids))
    async with db.execute(
        f"SELECT id FROM tracks WHERE session_id IN ({placeholders})", session_ids
    ) as cursor:
        track_rows = await cursor.fetchall()
    track_ids = [row[0] for row in track_rows]

    # FK-safe order: tracks and session_members reference sessions, so delete
    # them before the sessions row itself.
    await db.execute(f"DELETE FROM tracks WHERE session_id IN ({placeholders})", session_ids)
    await db.execute(
        f"DELETE FROM session_members WHERE session_id IN ({placeholders})", session_ids
    )
    await db.execute(f"DELETE FROM sessions WHERE id IN ({placeholders})", session_ids)
    await db.commit()

    # Gracefully close out any connection still live for a session we just
    # deleted, rather than just dropping it from bookkeeping and leaving its
    # socket dangling. Broadcasting first, then closing, means a straggler
    # client is told why its session just ended instead of silently losing
    # it.
    #
    # This runs AFTER the DB deletes (and their commit) above, not before:
    # `close_session` awaits (broadcasting, then closing sockets), which
    # yields the event loop. If the DB deletes ran after this instead, a new
    # websocket connect for the same session_id could slip in during that
    # window, pass `_is_active_member`/session-exists checks (the row still
    # being present), get re-added to `manager.active`, and then never
    # receive `session_ended` — and since the session row is about to
    # vanish, no future sweep would ever find that session_id again to clean
    # it up, leaving an orphaned connection with no cleanup path. Deleting
    # first closes that race: any connect attempt racing in during/after the
    # delete now hits a session-exists check that already sees the row gone.
    for session_id in session_ids:
        if session_id in manager.active:
            await manager.close_session(
                session_id, "session_ended", {"reason": "expired"}
            )

    for track_id in track_ids:
        await asyncio.to_thread(
            shutil.rmtree, Path(storage_dir) / "tracks" / track_id, ignore_errors=True
        )

    logger.info("reaper: reaped %d expired session(s)", len(session_ids))
    return len(session_ids)


async def run_reaper_loop(storage_dir: str, ttl_seconds: float, interval_seconds: float) -> None:
    """Infinite loop: touch actively-connected sessions, sweep for expired
    ones, sleep, repeat. A failure in one iteration is logged and does not
    kill the loop."""
    while True:
        try:
            db = await get_db()
            await _touch_active_connections(db)
            await reap_expired_sessions(storage_dir, ttl_seconds)
        except Exception:
            logger.exception("reaper: sweep iteration failed")
        await asyncio.sleep(interval_seconds)
