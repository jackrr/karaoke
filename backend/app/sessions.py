"""Session management service."""
import secrets
import time
from typing import Optional

from app.db import get_db, Database
from .schema import Session, Client


def generate_passcode() -> str:
    """Generate random 6-digit numeric passcode."""
    return str(secrets.randbelow(1000000)).zfill(6)


async def create_session(host_id: str, db: Optional[Database] = None) -> Session:
    """Create a new session with a random passcode."""
    if db is None:
        db = get_db()

    passcode = generate_passcode()
    session_id = secrets.token_hex(16)
    now = int(time.time())

    await db.execute(
        "INSERT INTO sessions (id, passcode, host_id, status, created_at, updated_at, expires_at) "
        "VALUES (?, ?, ?, 'active', ?, ?, ?)",
        (session_id, passcode, host_id, now, now, now + 86400),
    )

    return Session(
        id=session_id,
        passcode=passcode,
        host_id=host_id,
        status="active",
        created_at=now,
        updated_at=now,
        expires_at=now + 86400,
    )


async def join_session(
    passcode: str, client_id: str, db: Optional[Database] = None
) -> Optional[Session]:
    """Join a session by passcode. First joiner becomes host."""
    if db is None:
        db = get_db()

    row = await db.query_one(
        "SELECT id, passcode, host_id, status, created_at, updated_at, expires_at "
        "FROM sessions WHERE passcode = ? AND status = 'active'",
        (passcode,),
    )
    if not row:
        return None

    session = Session(**row)

    if session.host_id is None:
        await db.execute(
            "UPDATE sessions SET host_id = ? WHERE id = ?",
            (client_id, session.id),
        )

    return session


async def get_session_by_passcode(
    passcode: str, db: Optional[Database] = None
) -> Optional[Session]:
    """Get a session by passcode."""
    if db is None:
        db = get_db()

    row = await db.query_one(
        "SELECT id, passcode, host_id, status, created_at, updated_at, expires_at "
        "FROM sessions WHERE passcode = ? AND status = 'active'",
        (passcode,),
    )
    return Session(**row) if row else None


async def get_session_by_id(session_id: str, db: Optional[Database] = None) -> Optional[Session]:
    """Get a session by ID."""
    if db is None:
        db = get_db()

    row = await db.query_one(
        "SELECT id, passcode, host_id, status, created_at, updated_at, expires_at "
        "FROM sessions WHERE id = ?",
        (session_id,),
    )
    return Session(**row) if row else None


async def expire_stale_sessions(db: Optional[Database] = None) -> int:
    """Expire sessions older than 24h of inactivity. Returns count of expired sessions."""
    if db is None:
        db = get_db()

    now = int(time.time())
    async with db.connection() as conn:
        await conn.execute(
            "UPDATE sessions SET status = 'gone' "
            "WHERE status = 'active' AND updated_at < ? AND expires_at < ?",
            (now - 86400, now - 86400),
        )
        expired_count = conn.rowcount if hasattr(conn, "cursor") else 0

    return expired_count


async def get_session_clients(
    session_id: str, db: Optional[Database] = None
) -> list[Client]:
    """Get all clients for a session."""
    if db is None:
        db = get_db()

    rows = await db.query_all(
        "SELECT client_id, session_id, client_type, joined_at, connected, last_seen "
        "FROM clients WHERE session_id = ? AND connected = 1",
        (session_id,),
    )
    return [Client(**row) for row in rows]


async def add_client(
    session_id: str,
    client_id: str,
    client_type: str,
    db: Optional[Database] = None,
) -> Client:
    """Add a client to a session."""
    if db is None:
        db = get_db()

    now = int(time.time())
    try:
        await db.execute(
            "INSERT INTO clients (id, session_id, client_id, client_type, joined_at, connected, last_seen) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (secrets.token_hex(16), session_id, client_id, client_type, now, now),
        )
    except Exception:
        await db.execute(
            "UPDATE clients SET connected = 1, last_seen = ?, client_type = ? "
            "WHERE session_id = ? AND client_id = ?",
            (now, client_type, session_id, client_id),
        )

    return Client(
        client_id=client_id,
        session_id=session_id,
        client_type=client_type,
        joined_at=now,
        connected=1,
        last_seen=now,
    )


async def remove_client(session_id: str, client_id: str, db: Optional[Database] = None) -> None:
    """Mark a client as disconnected."""
    if db is None:
        db = get_db()

    await db.execute(
        "UPDATE clients SET connected = 0 WHERE session_id = ? AND client_id = ?",
        (session_id, client_id),
    )
