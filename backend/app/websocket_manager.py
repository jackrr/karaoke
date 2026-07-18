import json
from typing import Dict, Set

import anyio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from .database import get_db


class ConnectionManager:
    """Tracks live websocket connections per session, per client.

    Keyed as session_id -> client_id -> set of live WebSockets, so multiple
    concurrent connections from the same client_id (e.g. two browser tabs
    sharing one persisted localStorage identity) coexist independently
    instead of one silently overwriting the other's entry.
    """

    def __init__(self) -> None:
        self.active: Dict[str, Dict[str, Set[WebSocket]]] = {}

    async def connect(self, session_id: str, client_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active.setdefault(session_id, {}).setdefault(client_id, set()).add(ws)

    def discard(self, session_id: str, client_id: str, ws: WebSocket) -> None:
        """Remove exactly the given socket — never any other connection that
        happens to share the same client_id."""
        session_conns = self.active.get(session_id)
        if session_conns is None:
            return
        client_conns = session_conns.get(client_id)
        if client_conns is None:
            return
        client_conns.discard(ws)
        if not client_conns:
            del session_conns[client_id]
        if not session_conns:
            del self.active[session_id]

    async def broadcast(self, session_id: str, message: str) -> None:
        dead: list[tuple[str, WebSocket]] = []
        for client_id, sockets in list(self.active.get(session_id, {}).items()):
            for ws in list(sockets):
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append((client_id, ws))
        for client_id, ws in dead:
            self.discard(session_id, client_id, ws)

    async def broadcast_event(self, session_id: str, event_type: str, data: dict) -> None:
        await self.broadcast(session_id, json.dumps({"type": event_type, "data": data}))

    def has_connection(self, session_id: str, client_id: str) -> bool:
        """True if this client_id still has at least one live socket in this
        session (e.g. another browser tab)."""
        return bool(self.active.get(session_id, {}).get(client_id))


manager = ConnectionManager()

ws_router = APIRouter()


async def _is_active_member(session_id: str, client_id: str) -> bool:
    db = await get_db()
    async with db.execute(
        "SELECT 1 FROM session_members WHERE session_id = ? AND client_id = ? AND left_at IS NULL",
        (session_id, client_id),
    ) as cursor:
        row = await cursor.fetchone()
    return row is not None


async def _mark_member_left(session_id: str, client_id: str) -> None:
    """Mirror `leave_session`'s DB update so a dropped websocket (tab closed,
    network loss) doesn't leave a member showing as active forever. Guarded
    by `left_at IS NULL` so this is idempotent alongside an explicit
    `leave_session` call for the same client."""
    db = await get_db()
    await db.execute(
        "UPDATE session_members SET left_at = CURRENT_TIMESTAMP "
        "WHERE session_id = ? AND client_id = ? AND left_at IS NULL",
        (session_id, client_id),
    )
    await db.commit()


@ws_router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str, client_id: str = Query(...)
) -> None:
    if not await _is_active_member(session_id, client_id):
        # Reject before accepting — this closes the handshake with a policy
        # violation rather than opening then immediately dropping.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(session_id, client_id, websocket)
    await manager.broadcast_event(session_id, "member_joined", {"client_id": client_id})
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        manager.discard(session_id, client_id, websocket)
        # Only mark the member "left" in the DB (and broadcast member_left)
        # once none of this client_id's other connections (e.g. another
        # browser tab) are still live for this session.
        if not manager.has_connection(session_id, client_id):
            # Shielded: a WebSocketDisconnect here is delivered by cancelling
            # this connection's own task scope (e.g. the client closing the
            # socket), so further awaits below would otherwise immediately
            # observe that same cancellation and never complete. This cleanup
            # — persisting the member's departure and telling everyone else —
            # must run to completion regardless.
            with anyio.CancelScope(shield=True):
                await _mark_member_left(session_id, client_id)
                await manager.broadcast_event(session_id, "member_left", {"client_id": client_id})
