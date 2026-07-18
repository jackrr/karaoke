import asyncio

from app import database


async def test_concurrent_get_db_does_not_race(tmp_path) -> None:
    """Regression: concurrent first-callers must not double-await the connect task.

    Runs against its own connection (module state is saved/restored) so it doesn't
    disturb the shared connection the other tests' autouse fixture depends on.
    """
    saved_conn, saved_task = database._db_conn, database._db_connect_task
    database._db_conn = None
    database._db_connect_task = None
    try:
        database.start_db(str(tmp_path / "concurrent.db"))
        conns = await asyncio.gather(*(database.get_db() for _ in range(10)))
        assert all(conn is conns[0] for conn in conns)
        await conns[0].close()
    finally:
        database._db_conn, database._db_connect_task = saved_conn, saved_task
