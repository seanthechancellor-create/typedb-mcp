"""The tools the MCP server actually exposes to a client."""
import asyncio

from fastmcp import Client

from server import mcp

EXPECTED = {
    "query",
    "database_list",
    "database_create",
    "database_delete",
    "database_schema",
    "database_type_schema",
    "transaction_open",
    "transaction_query",
    "transaction_commit",
    "transaction_close",
    "user_list",
    "user_create",
    "user_delete",
}


def _tool_names():
    async def go():
        async with Client(mcp) as client:
            return {t.name for t in await client.list_tools()}

    return asyncio.run(go())


def test_every_expected_tool_is_registered():
    assert EXPECTED <= _tool_names()


def test_transaction_tools_are_reachable_by_a_client():
    """Registration alone is not enough -- they must be callable."""
    assert {"transaction_open", "transaction_commit"} <= _tool_names()
