"""Test fixtures. These run against a REAL local TypeDB server, not mocks.

The scratch database is created and dropped per-session so tests never touch
`loom` or `socip`. Nothing here reads credentials from the command line.
"""
import os
import uuid

import pytest

import config
from database import create_database, delete_database
from query import query as one_shot_query

# An empty database cannot answer `match $x isa $t` at all -- type inference
# fails with INF11 when no types exist. Every scratch db gets one type.
SCRATCH_SCHEMA = "define entity widget, owns tag; attribute tag, value string;"

LOCAL_URL = os.environ.get("TYPEDB_TEST_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session", autouse=True)
def _point_at_local_server():
    """server.py normally sets these from argv; tests set them directly."""
    config.TYPEDB_URL = LOCAL_URL
    config.TYPEDB_USERNAME = os.environ.get("TYPEDB_TEST_USERNAME", "admin")
    config.TYPEDB_PASSWORD = os.environ.get("TYPEDB_TEST_PASSWORD", "password")
    yield


@pytest.fixture(scope="session", autouse=True)
def _sweep_stray_scratch_dbs(_point_at_local_server):
    """Delete leftover scratch databases before and after the session.

    A transaction left open pins its database, so a failing test can defeat
    the per-test teardown. Without this sweep those leak and accumulate
    alongside the real `loom` and `socip`.
    """
    def sweep():
        import json

        from database import list_databases
        for db in json.loads(list_databases())["databases"]:
            if db["name"].startswith("mcptest_"):
                try:
                    delete_database(db["name"])
                except Exception as exc:  # noqa: BLE001 - best effort cleanup
                    print(f"could not delete stray {db['name']}: {exc}")

    sweep()
    yield
    sweep()


@pytest.fixture
def scratch_db(_point_at_local_server):
    """A throwaway database. Dropped even if the test fails."""
    name = f"mcptest_{uuid.uuid4().hex[:10]}"
    create_database(name)
    try:
        one_shot_query(SCRATCH_SCHEMA, name, "schema")
        yield name
    finally:
        delete_database(name)
