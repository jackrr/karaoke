"""WebSocket message and data models for the WebSocket manager."""
import uuid
from typing import Optional
from enum import Enum

from pydantic import BaseModel


class Session(BaseModel):
    id: str
    passcode: str
    host_id: Optional[str] = None
    status: str = "active"
    created_at: int = 0
    updated_at: int = 0
    expires_at: int = 0


class Client(BaseModel):
    client_id: str
    session_id: str
    client_type: str = "guest"
    joined_at: int = 0
    connected: int = 1
    last_seen: int = 0


class ClientType(str, Enum):
    host = "host"
    guest = "guest"


class TrackSource(str, Enum):
    youtube = "youtube"
    upload = "upload"
    jellyfin = "jellyfin"


class QueueStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"


class QueueEntry(BaseModel):
    id: str
    session_id: str
    track_id: Optional[str] = None
    position: int = 0
    status: str = "pending"
    added_by: str = ""
    source: str = "youtube"
    metadata: Optional[dict] = None
    added_at: int = 0


def make_ws_message(msg_type: str, data: Optional[dict] = None) -> dict:
    """Create a WebSocket message dict."""
    import time
    return {
        "type": msg_type,
        "data": data,
        "timestamp": int(time.time()),
    }
