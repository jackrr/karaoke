import re

from httpx import AsyncClient

import app.main as main_module
from app.main import _upsert_member
from app.database import get_db


async def _create_session(
    async_client: AsyncClient, name: str = "s", display_name: str = "Host"
) -> dict:
    resp = await async_client.post("/sessions", json={"name": name, "display_name": display_name})
    assert resp.status_code == 201
    return resp.json()


async def test_passcode_is_six_digits(async_client: AsyncClient) -> None:
    data = await _create_session(async_client)
    assert re.fullmatch(r"\d{6}", data["passcode"])


async def test_passcode_unique_retries_on_collision(
    async_client: AsyncClient, monkeypatch
) -> None:
    """A collision on the second session's first attempt should trigger a retry."""
    values = iter([5, 5, 6])
    monkeypatch.setattr(main_module.secrets, "randbelow", lambda _n: next(values))

    first = await _create_session(async_client, name="s1")
    second = await _create_session(async_client, name="s2")

    assert first["passcode"] == "000005"
    assert second["passcode"] == "000006"


async def test_join_with_correct_passcode_succeeds(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={"passcode": created["passcode"], "display_name": "Guest"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["is_host"] is False
    assert data["client_id"]
    assert data["client_id"] != created["host_client_id"]


async def test_join_with_wrong_passcode_fails(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)

    resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={"passcode": "000000" if created["passcode"] != "000000" else "111111",
              "display_name": "Guest"},
    )
    assert resp.status_code == 403


async def test_join_unknown_session_404(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions/nonexistent-id/join",
        json={"passcode": "123456", "display_name": "Guest"},
    )
    assert resp.status_code == 404


async def test_join_by_passcode_succeeds(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)

    resp = await async_client.post(
        "/sessions/join",
        json={"passcode": created["passcode"], "display_name": "Guest"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["is_host"] is False


async def test_join_by_unknown_passcode_404(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/sessions/join",
        json={"passcode": "000000", "display_name": "Guest"},
    )
    assert resp.status_code == 404


async def test_get_session_shows_participants_including_host(async_client: AsyncClient) -> None:
    created = await _create_session(async_client, display_name="Hosty")

    resp = await async_client.get(f"/sessions/{created['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["passcode"] == created["passcode"]
    assert data["host_client_id"] == created["host_client_id"]
    assert data["participants"] == [
        {
            "client_id": created["host_client_id"],
            "display_name": "Hosty",
            "is_host": True,
        }
    ]


async def test_get_session_includes_joined_guest(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)
    join_resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={"passcode": created["passcode"], "display_name": "Guest"},
    )
    guest_client_id = join_resp.json()["client_id"]

    resp = await async_client.get(f"/sessions/{created['id']}")
    participants = resp.json()["participants"]
    assert len(participants) == 2
    guest_entries = [p for p in participants if p["client_id"] == guest_client_id]
    assert guest_entries == [
        {"client_id": guest_client_id, "display_name": "Guest", "is_host": False}
    ]


async def test_leave_marks_member_gone(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)
    join_resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={"passcode": created["passcode"], "display_name": "Guest"},
    )
    guest_client_id = join_resp.json()["client_id"]

    leave_resp = await async_client.post(
        f"/sessions/{created['id']}/leave", json={"client_id": guest_client_id}
    )
    assert leave_resp.status_code == 204

    resp = await async_client.get(f"/sessions/{created['id']}")
    participants = resp.json()["participants"]
    assert all(p["client_id"] != guest_client_id for p in participants)
    # host is still present
    assert any(p["client_id"] == created["host_client_id"] for p in participants)


async def test_create_session_with_client_supplied_client_id(async_client: AsyncClient) -> None:
    """Creating a session should adopt a caller-supplied client_id as the
    host_client_id, rather than always minting a new one — this keeps a
    browser's existing persisted identity intact when it hosts a new
    session (fix for the create-overwrites-existing-identity bug)."""
    resp = await async_client.post(
        "/sessions",
        json={
            "name": "s",
            "display_name": "Host",
            "client_id": "already-persisted-client-id",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["host_client_id"] == "already-persisted-client-id"
    assert data["client_id"] == "already-persisted-client-id"


async def test_create_session_without_client_id_mints_one(async_client: AsyncClient) -> None:
    data = await _create_session(async_client)
    assert data["host_client_id"]
    assert data["client_id"] == data["host_client_id"]


async def test_passcode_collision_on_insert_retries(
    async_client: AsyncClient, monkeypatch
) -> None:
    """Even if the pre-check SELECT misses a race (two concurrent creates),
    a collision surfacing as an IntegrityError on the INSERT itself should
    trigger a retry with a freshly generated passcode, not an unhandled 500."""
    await _create_session(async_client, name="existing")
    db = await get_db()
    async with db.execute("SELECT passcode FROM sessions WHERE name = 'existing'") as cursor:
        row = await cursor.fetchone()
    assert row is not None
    (taken_passcode,) = row

    # Force the passcode pre-check to always report "unique" so the only
    # thing preventing a collision is the INSERT's UNIQUE constraint —
    # simulating a race the pre-check missed.
    call_count = {"n": 0}

    async def fake_generate_unique_passcode(_db):
        call_count["n"] += 1
        return taken_passcode if call_count["n"] == 1 else "999999"

    monkeypatch.setattr(main_module, "_generate_unique_passcode", fake_generate_unique_passcode)

    resp = await async_client.post(
        "/sessions", json={"name": "new-session", "display_name": "Host"}
    )
    assert resp.status_code == 201
    assert resp.json()["passcode"] == "999999"
    assert call_count["n"] == 2


async def test_upsert_member_twice_does_not_duplicate(async_client: AsyncClient) -> None:
    """Calling _upsert_member twice for the same (session_id, client_id) —
    simulating two concurrent join requests for the same client — must not
    create duplicate participant rows."""
    created = await _create_session(async_client)
    db = await get_db()

    await _upsert_member(db, created["id"], "dup-client", "Guest")
    await _upsert_member(db, created["id"], "dup-client", "Guest Renamed")

    async with db.execute(
        "SELECT COUNT(*), display_name FROM session_members WHERE session_id = ? AND client_id = ?",
        (created["id"], "dup-client"),
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    count, display_name = row
    assert count == 1
    assert display_name == "Guest Renamed"


async def test_rejoin_after_leave_clears_left_at(async_client: AsyncClient) -> None:
    created = await _create_session(async_client)
    join_resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={"passcode": created["passcode"], "display_name": "Guest"},
    )
    guest_client_id = join_resp.json()["client_id"]

    await async_client.post(f"/sessions/{created['id']}/leave", json={"client_id": guest_client_id})

    rejoin_resp = await async_client.post(
        f"/sessions/{created['id']}/join",
        json={
            "passcode": created["passcode"],
            "display_name": "Guest Again",
            "client_id": guest_client_id,
        },
    )
    assert rejoin_resp.status_code == 200
    assert rejoin_resp.json()["client_id"] == guest_client_id

    resp = await async_client.get(f"/sessions/{created['id']}")
    participants = resp.json()["participants"]
    guest_entries = [p for p in participants if p["client_id"] == guest_client_id]
    assert guest_entries == [
        {"client_id": guest_client_id, "display_name": "Guest Again", "is_host": False}
    ]
