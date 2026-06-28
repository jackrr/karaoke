"""Pydantic data models for session management, queue, tracks, clients, and processing jobs."""
from typing import Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    active = "active"
    idle = "idle"
    gone = "gone"


class ClientType(str, Enum):
    host = "host"
    guest = "guest"


class ConnectionState(str, Enum):
    idle = "idle"
    connecting = "connecting"
    connected = "connected"
    reconnecting = "reconnecting"
    disconnected = "disconnected"


class TrackSource(str, Enum):
    youtube = "youtube"
    upload = "upload"
    jellyfin = "jellyfin"


class TrackStatus(str, Enum):
    processing = "processing"
    ready = "ready"
    error = "error"


class QueueStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"


class ProcessingStage(str, Enum):
    downloading = "downloading"
    identifying = "identifying"
    lyrics = "lyrics"
    stemming = "stemming"
    mixing = "mixing"


class Session(BaseModel):
    id: str
    passcode: str
    host_id: Optional[str] = None
    status: SessionStatus = SessionStatus.active
    created_at: int = 0
    updated_at: int = 0
    expires_at: int = 0


class SessionCreate(BaseModel):
    client_id: str


class SessionJoin(BaseModel):
    passcode: str
    client_id: str
    client_type: ClientType = ClientType.guest


class Client(BaseModel):
    client_id: str
    session_id: str
    client_type: ClientType
    joined_at: int = 0
    connected: int = 1
    last_seen: int = 0


class Track(BaseModel):
    id: str
    hash: Optional[str] = None
    title: str = ""
    artist: Optional[str] = None
    duration: Optional[float] = None
    storage_path: Optional[str] = None
    stem_files: Optional[dict] = None
    lyrics_format: str = "none"
    lyrics_source: Optional[str] = None
    lyric_lines: Optional[list[dict]] = None
    fallback_text: Optional[str] = None
    status: TrackStatus = TrackStatus.processing
    created_at: int = 0


class QueueEntry(BaseModel):
    id: str
    session_id: str
    track_id: Optional[str] = None
    position: int = 0
    status: QueueStatus = QueueStatus.pending
    added_by: str = ""
    source: str = "youtube"
    metadata: Optional[dict] = None
    added_at: int = 0


class QueueEntryCreate(BaseModel):
    source: TrackSource
    source_url: str
    client_id: str


class QueueReorder(BaseModel):
    new_position: int
    client_id: str


class ProcessingJob(BaseModel):
    id: str
    queue_entry_id: Optional[str] = None
    stage: ProcessingStage
    progress: float = 0.0
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    error: Optional[str] = None
    device: str = "auto"


class QueueSnapshot(BaseModel):
    current_track: Optional[Track] = None
    queue: list[QueueEntry] = []
    clients: list[Client] = []
    session: Optional[Session] = None


# WebSocket message types
class WSMessageType(str, Enum):
    # State updates from server to client
    SESSION_UPDATE = "session_update"
    QUEUE_UPDATE = "queue_update"
    TRACK_UPDATE = "track_update"
    CLIENT_UPDATE = "client_update"
    LYRICS_UPDATE = "lyrics_update"
    PROCESSING_UPDATE = "processing_update"
    RECOVERY = "recovery"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    AUDIO_POSITION = "audio_position"

    # Client to server
    ENQUEUE = "enqueue"
    REORDER = "reorder"
    REMOVE = "remove"
    CLEAR = "clear"
    SEEK = "seek"
    JOIN = "join"
    LEAVE = "leave"


class WSMessage(BaseModel):
    type: str
    data: Optional[dict] = None
    timestamp: Optional[int] = None


def make_ws_message(msg_type: str, data: Optional[dict] = None) -> dict:
    """Create a WebSocket message dict."""
    return WSMessage(
        type=msg_type,
        data=data,
        timestamp=int(datetime.now().timestamp())
    ).model_dump()


class PlaybackState(BaseModel):
    session_id: str
    track_id: str
    current_position: float
    is_playing: bool
    started_at: Optional[int] = None
