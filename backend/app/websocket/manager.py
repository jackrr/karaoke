"""WebSocket connection manager for real-time communication."""
import asyncio
import uuid
from typing import Dict, Set, Optional

from app.websocket.schema import Client, make_ws_message, Session, ClientType
from app.websocket.schema import QueueEntry as WSQueueEntry


class WebSocketManager:
    """Manages WebSocket connections, broadcasts, and client state."""

    def __init__(self):
        # {client_id: ws}
        self.active_connections: Dict[str, "WebSocket"] = {}
        # {session_id: {client_id}}
        self.session_members: Dict[str, Set[str]] = {}
        # {client_id: session_id}
        self.client_sessions: Dict[str, str] = {}
        # {client_id: disconnect_time}
        self.client_disconnects: Dict[str, float] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 15  # seconds

    def start_heartbeat(self):
        """Start the server heartbeat task."""
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send heartbeat pings every interval."""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            for client_id, ws in list(self.active_connections.items()):
                try:
                    await ws.send_json(make_ws_message("heartbeat"))
                except Exception:
                    pass

    async def handle_connection(self, websocket, session_id: str):
        """Handle a full WebSocket lifecycle."""
        client_id = str(uuid.uuid4())
        try:
            await websocket.accept()
        except Exception:
            return

        await self.connect(
            websocket=websocket,
            session_id=session_id,
            client_id=client_id,
            client_type="guest",
        )
        await self._listen(websocket, client_id)

    async def connect(self, websocket, session_id: str, client_id: Optional[str] = None, client_type: str = ClientType.guest.value) -> str:
        """Connect a WebSocket and return its client_id."""
        if client_id is None:
            client_id = str(uuid.uuid4())

        self.active_connections[client_id] = websocket
        self.client_sessions[client_id] = session_id

        if session_id not in self.session_members:
            self.session_members[session_id] = set()
        self.session_members[session_id].add(client_id)

        # Send full state snapshot to the connected client
        snapshot = await self._get_state_snapshot(session_id)
        await websocket.send_json(make_ws_message("snapshot", snapshot))

        # Broadcast client list to all in session
        await self._broadcast_to_session(session_id, make_ws_message("updateClients", {
            "type": "joined",
            "client": {
                "client_id": client_id,
                "client_type": client_type,
                "session_id": session_id,
            },
        }))

        return client_id

    async def _listen(self, websocket, client_id: str):
        """Read messages from the connected WebSocket."""
        try:
            async for message in websocket.iter_json():
                await self.handle_message(client_id, message)
        except Exception:
            pass
        finally:
            await self.disconnect(websocket, client_id)

    async def disconnect(self, websocket, client_id: str):
        """Handle a WebSocket disconnect."""
        session_id = self.client_sessions.pop(client_id, None)

        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if session_id and session_id in self.session_members:
            self.session_members[session_id].discard(client_id)

        self.client_disconnects[client_id] = asyncio.get_event_loop().time()

        # Notify others in session
        if session_id:
            await self._broadcast_to_session(session_id, make_ws_message("updateClients", {
                "type": "left",
                "client_id": client_id,
            }))

    async def broadcast(self, session_id: str, message: dict):
        """Broadcast a message to all clients in a session."""
        ws_list = list(self.session_members.get(session_id, set()))
        for client_id in ws_list:
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    async def _broadcast_to_session(self, session_id: str, message: dict):
        """Internal helper to broadcast to session."""
        await self.broadcast(session_id, message)

    async def handle_message(self, client_id: str, msg_data: dict):
        """Handle incoming messages from clients."""
        session_id = self.client_sessions.get(client_id)
        if not session_id:
            return

        msg_type = msg_data.get("type", "")
        from app.api.routes.queue import enqueue, reorder, remove, clear_session
        from app.schema import QueueEntryCreate

        if msg_type == "enqueue":
            source = msg_data.get("source", {}).get("type", "youtube")
            source_url = msg_data.get("source", {}).get("url", "")
            if source and source_url:
                db_obj = await _get_db()
                entry = await enqueue(
                    QueueEntryCreate(source=source, source_url=source_url, client_id=client_id),
                    session_id, db_obj,
                )
                await self.broadcast(session_id, make_ws_message("updateQueue", {
                    "type": "added",
                    "entry": entry.model_dump(),
                }))

        elif msg_type == "reorder":
            from app.queue import reorder as do_reorder
            try:
                db_obj = await _get_db()
                updated = await do_reorder(
                    msg_data.get("entry_id"),
                    msg_data.get("new_position", 0),
                    client_id,
                    db_obj,
                )
                await self.broadcast(session_id, make_ws_message("updateQueue", {
                    "type": "reordered",
                    "entry": updated.model_dump(),
                }))
            except ValueError:
                ws = self.active_connections.get(client_id)
                if ws:
                    await ws.send_json(make_ws_message("error", {"message": "Queue entry not found"}))

        elif msg_type == "remove":
            db_obj = await _get_db()
            await remove(msg_data.get("entry_id"), client_id, db_obj)
            await self.broadcast(session_id, make_ws_message("updateQueue", {
                "type": "removed",
                "entry_id": msg_data.get("entry_id"),
            }))

        elif msg_type == "clear":
            db_obj = await _get_db()
            await clear_session(session_id, client_id, db_obj)
            await self.broadcast(session_id, make_ws_message("updateQueue", {
                "type": "cleared",
                "queue": [],
            }))

        elif msg_type == "audio_position":
            await self.broadcast(session_id, make_ws_message("audioPosition", {
                "client_id": client_id,
                "currentTime": msg_data.get("currentTime", 0),
            }))

        # Would update last active time in DB here

    async def _get_state_snapshot(self, session_id: str) -> dict:
        """Get full state snapshot for a session (for reconnection)."""
        db_obj = await _get_db()
        from app.sessions import get_session_by_id, get_session_clients
        from app.queue import get_queue

        session = await get_session_by_id(session_id, db_obj)
        clients = await get_session_clients(session_id, db_obj)

        queue_entries = []
        if session:
            queue_entries = await get_queue(session_id, db_obj)

        # Get current track
        current_track = None
        cursor = await db_obj.execute(
            "SELECT * FROM tracks t JOIN queue_entries qe ON t.id = qe.track_id "
            "WHERE qe.session_id = ? AND qe.status = 'playing' LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row:
            cols = [d[0] for d in cursor.description]
            current_track = dict(zip(cols, row))

        return {
            "session": session.model_dump() if session else None,
            "queue": [e.model_dump() for e in queue_entries],
            "track": current_track,
            "clients": [c.model_dump() for c in clients],
        }

    def get_session_members(self, session_id: str) -> Set[str]:
        return self.session_members.get(session_id, set())

    def is_connected(self, client_id: str) -> bool:
        return client_id in self.active_connections

    def get_client_type(self, client_id: str) -> Optional[str]:
        session_id = self.client_sessions.get(client_id)
        if not session_id:
            return None
        return "guest"


from fastapi import WebSocket
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    WebSocket = WebSocket  # type: ignore[misc]
else:
    WebSocket = object  # forward reference


async def _get_db():
    """Lazily import and get the DB instance."""
    from app.db import get_db
    db = get_db()
    return await db.connection()
