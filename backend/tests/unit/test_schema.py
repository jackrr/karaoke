"""Tests for app.schema – Pydantic model validation, enums, and helpers."""
from pydantic import ValidationError
import pytest

from app.schema import (
    Session, SessionCreate, SessionJoin, ClientType, ConnectionState,
    SessionStatus, TrackSource, TrackStatus, QueueStatus, ProcessingStage,
    Client, Track, QueueEntry, QueueEntryCreate, QueueReorder,
    ProcessingJob, QueueSnapshot, WSMessageType, WSMessage,
    PlaybackState, make_ws_message,
)


# ── SessionStatus enum ──


class TestSessionStatus:
    def test_active_value(self):
        assert SessionStatus.active == "active"

    def test_idle_value(self):
        assert SessionStatus.idle == "idle"

    def test_gone_value(self):
        assert SessionStatus.gone == "gone"

    def test_valid_from_string(self):
        assert SessionStatus("active") is SessionStatus.active

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            SessionStatus("unknown")


# ── ClientType enum ──


class TestClientType:
    def test_host(self):
        assert ClientType.host == "host"

    def test_guest(self):
        assert ClientType.guest == "guest"


# ── ConnectionStatue enum ──


class TestConnectionState:
    def test_connected(self):
        assert ConnectionState.connected == "connected"

    def test_disconnected(self):
        assert ConnectionState.disconnected == "disconnected"


# ── TrackSource enum ──


class TestTrackSource:
    def test_youtube(self):
        assert TrackSource.youtube.value == "youtube"

    def test_upload(self):
        assert TrackSource.upload.value == "upload"

    def test_jellyfin(self):
        assert TrackSource.jellyfin.value == "jellyfin"

    def test_to_lower(self):
        assert TrackSource.youtube.lower() == "youtube"
        assert TrackSource.jellyfin.lower() == "jellyfin"


# ── QueueStatus enum ──


class TestQueueStatus:
    def test_pending(self):
        assert QueueStatus.pending == "pending"

    def test_processing(self):
        assert QueueStatus.processing == "processing"

    def test_ready(self):
        assert QueueStatus.ready == "ready"

    def test_error(self):
        assert QueueStatus.error == "error"


# ── TrackStatus enum ──


class TestTrackStatus:
    def test_processing(self):
        assert TrackStatus.processing == "processing"

    def test_ready(self):
        assert TrackStatus.ready == "ready"

    def test_error(self):
        assert TrackStatus.error == "error"


# ── ProcessingStage enum ──


class TestProcessingStage:
    def test_downloading(self):
        assert ProcessingStage.downloading == "downloading"

    def test_identifying(self):
        assert ProcessingStage.identifying == "identifying"

    def test_lyrics(self):
        assert ProcessingStage.lyrics == "lyrics"

    def test_stemming(self):
        assert ProcessingStage.stemming == "stemming"

    def test_mixing(self):
        assert ProcessingStage.mixing == "mixing"


# ── WSMessageType enum ──


class TestWSMessageType:
    def test_session_update(self):
        assert WSMessageType.SESSION_UPDATE == "session_update"

    def test_queue_update(self):
        assert WSMessageType.QUEUE_UPDATE == "queue_update"

    def test_enqueue(self):
        assert WSMessageType.ENQUEUE == "enqueue"

    def test_reorder(self):
        assert WSMessageType.REORDER == "reorder"

    def test_remove(self):
        assert WSMessageType.REMOVE == "remove"

    def test_clear(self):
        assert WSMessageType.CLEAR == "clear"

    def test_seek(self):
        assert WSMessageType.SEEK == "seek"

    def test_join(self):
        assert WSMessageType.JOIN == "join"

    def test_leave(self):
        assert WSMessageType.LEAVE == "leave"

    def test_error(self):
        assert WSMessageType.ERROR == "error"

    def test_heartbeat(self):
        assert WSMessageType.HEARTBEAT == "heartbeat"

    def test_audio_position(self):
        assert WSMessageType.AUDIO_POSITION == "audio_position"

    def test_recovery(self):
        assert WSMessageType.RECOVERY == "recovery"

    def test_lyrics_update(self):
        assert WSMessageType.LYRICS_UPDATE == "lyrics_update"

    def test_processing_update(self):
        assert WSMessageType.PROCESSING_UPDATE == "processing_update"

    def test_all_types_are_strings(self):
        for member in WSMessageType:
            assert isinstance(member.value, str)


# ── Session model ──


class TestSession:
    def test_valid_session(self):
        s = Session(id="s-1", passcode="ABC123")
        assert s.id == "s-1"
        assert s.passcode == "ABC123"
        assert s.host_id is None
        assert s.status == SessionStatus.active

    def test_full_session(self):
        s = Session(
            id="s-2",
            passcode="XYZ789",
            host_id="c-1",
            status=SessionStatus.idle,
            created_at=100,
            updated_at=200,
            expires_at=300,
        )
        assert s.host_id == "c-1"
        assert s.status == SessionStatus.idle

    def test_serialization_roundtrip(self):
        s = Session(id="s-3", passcode="PASS1", host_id="host1", created_at=100)
        dump = s.model_dump()
        s2 = Session.model_validate(dump)
        assert s2.id == s.id
        assert s2.passcode == s.passcode

    def test_dict_dump(self):
        s = Session(id="s-4", passcode="P4")
        d = s.model_dump()
        assert d["id"] == "s-4"
        assert d["passcode"] == "P4"
        assert d["host_id"] is None
        assert d["status"] == "active"


# ── SessionCreate model ──


class TestSessionCreate:
    def test_valid(self):
        sc = SessionCreate(client_id="c-1")
        assert sc.client_id == "c-1"

    def test_missing_client_id_raises(self):
        with pytest.raises(ValidationError):
            SessionCreate()


# ── SessionJoin model ──


class TestSessionJoin:
    def test_valid(self):
        sj = SessionJoin(passcode="123456", client_id="c-2", client_type=ClientType.guest)
        assert sj.passcode == "123456"
        assert sj.client_type == ClientType.guest

    def test_default_guest(self):
        sj = SessionJoin(passcode="123456", client_id="c-2")
        assert sj.client_type == ClientType.guest

    def test_host_type(self):
        sj = SessionJoin(passcode="123456", client_id="c-2", client_type=ClientType.host)
        assert sj.client_type == ClientType.host


# ── Client model ──


class TestClient:
    def test_valid(self):
        c = Client(client_id="c-1", session_id="s-1", client_type=ClientType.host)
        assert c.connected == 1
        assert c.joined_at == 0
        assert c.last_seen == 0

    def test_serialization(self):
        c = Client(client_id="c-2", session_id="s-2", client_type=ClientType.guest, connected=0)
        d = c.model_dump()
        assert d["connected"] == 0


# ── Track model ──


class TestTrack:
    def test_minimal(self):
        t = Track(id="t-1")
        assert t.title == ""
        assert t.status == TrackStatus.processing

    def test_full(self):
        t = Track(
            id="t-2",
            hash="abc123",
            title="Test Song",
            artist="Test Artist",
            duration=240.5,
            storage_path="/tmp/test.mp3",
            stem_files={"vocals": "/vocals.mp3", "accompaniment": "/acomp.mp3"},
            lyrics_format="lrc",
            lyrics_source="lrclib",
            lyric_lines=[{"text": "line1", "time": 1.0}],
            fallback_text="No lyrics",
            status=TrackStatus.ready,
            created_at=1000,
        )
        assert t.artist == "Test Artist"
        assert t.lyric_lines[0]["text"] == "line1"


# ── QueueEntry model ──


class TestQueueEntry:
    def test_minimal(self):
        q = QueueEntry(id="e-1", session_id="s-1")
        assert q.status == QueueStatus.pending
        assert q.position == 0
        assert q.source == "youtube"

    def test_full(self):
        q = QueueEntry(
            id="e-2",
            session_id="s-2",
            track_id="t-1",
            position=5,
            status=QueueStatus.ready,
            added_by="c-1",
            source="jellyfin",
            metadata={"url": "http://example.com"},
            added_at=999,
        )
        assert q.position == 5
        assert q.status == QueueStatus.ready


# ── QueueEntryCreate model ──


class TestQueueEntryCreate:
    def test_valid_youtube(self):
        q = QueueEntryCreate(source=TrackSource.youtube, source_url="https://youtu.be/x", client_id="c-1")
        assert q.source == TrackSource.youtube

    def test_valid_upload(self):
        q = QueueEntryCreate(source=TrackSource.upload, source_url="/tmp/file.mp3", client_id="c-1")
        assert q.source == TrackSource.upload

    def test_valid_jellyfin(self):
        q = QueueEntryCreate(source=TrackSource.jellyfin, source_url="http://jf/item/1", client_id="c-1")
        assert q.source == TrackSource.jellyfin

    def test_missing_source_raises(self):
        with pytest.raises(ValidationError):
            QueueEntryCreate(source_url="url", client_id="c-1")


# ── QueueReorder model ──


class TestQueueReorder:
    def test_valid(self):
        r = QueueReorder(new_position=3, client_id="c-1")
        assert r.new_position == 3

    def test_position_zero(self):
        r = QueueReorder(new_position=0, client_id="c-1")
        assert r.new_position == 0


# ── ProcessingJob model ──


class TestProcessingJob:
    def test_default_values(self):
        pj = ProcessingJob(id="j-1", stage=ProcessingStage.downloading)
        assert pj.progress == 0.0
        assert pj.started_at is None
        assert pj.finished_at is None
        assert pj.error is None
        assert pj.device == "auto"

    def test_full(self):
        pj = ProcessingJob(
            id="j-2",
            queue_entry_id="e-1",
            stage=ProcessingStage.stemming,
            progress=0.5,
            started_at=100,
            finished_at=200,
            error=None,
            device="cpu",
        )
        assert pj.progress == 0.5
        assert pj.device == "cpu"


# ── QueueSnapshot model ──


class TestQueueSnapshot:
    def test_empty_snapshot(self):
        sn = QueueSnapshot()
        assert sn.current_track is None
        assert sn.queue == []
        assert sn.clients == []
        assert sn.session is None

    def test_with_data(self):
        s = Session(id="s-1", passcode="PASS")
        t = Track(id="t-1", title="Song", status=TrackStatus.ready)
        sn = QueueSnapshot(
            current_track=t,
            queue=[QueueEntry(id="e-1", session_id="s-1")],
            clients=[Client(client_id="c-1", session_id="s-1", client_type=ClientType.host)],
            session=s,
        )
        assert sn.current_track.id == "t-1"
        assert len(sn.queue) == 1


# ── WSMessage model ──


class TestWSMessage:
    def test_minimal_message(self):
        m = WSMessage(type="test", data={"foo": "bar"})
        assert m.type == "test"
        assert m.data == {"foo": "bar"}
        assert m.timestamp is None

    def test_serialization(self):
        m = WSMessage(type="enqueue", data={"url": "x"})
        d = m.model_dump()
        assert d["type"] == "enqueue"


def make_ws_message_test(msg_type: str, data: dict = None) -> dict:
    """Test helper wrapper."""
    return make_ws_message(msg_type, data)


class TestMakeWSMessage:
    def test_basic_message(self):
        msg = make_ws_message_test("enqueue", {"url": "https://youtu.be/x"})
        assert msg["type"] == "enqueue"
        assert msg["data"]["url"] == "https://youtu.be/x"
        assert "timestamp" in msg

    def test_message_without_data(self):
        msg = make_ws_message_test("heartbeat")
        assert msg["type"] == "heartbeat"
        assert "timestamp" in msg

    def test_message_timestamp_is_int(self):
        msg = make_ws_message_test("test")
        assert isinstance(msg["timestamp"], int)
        assert msg["timestamp"] > 0


# ── PlaybackState model ──


class TestPlaybackState:
    def test_valid(self):
        ps = PlaybackState(
            session_id="s-1",
            track_id="t-1",
            current_position=120.5,
            is_playing=True,
        )
        assert ps.current_position == 120.5
        assert ps.is_playing is True
        assert ps.started_at is None

    def test_serialization(self):
        ps = PlaybackState(session_id="s-1", track_id="t-1", current_position=0.0, is_playing=False)
        d = ps.model_dump()
        assert d["session_id"] == "s-1"
        assert d["is_playing"] is False

    def test_started_at(self):
        ps = PlaybackState(session_id="s", track_id="t", current_position=1.0, is_playing=True, started_at=100)
        assert ps.started_at == 100
