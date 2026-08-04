import argparse
import os
import signal
import sys
import logging
from fastmcp import FastMCP
import config
from query import query as execute_query
from database import list_databases as db_list, create_database as db_create, delete_database as db_delete, database_schema as db_schema, database_type_schema as db_type_schema
from user import list_users as usr_list, create_user as usr_create, delete_user as usr_delete
from transaction import (
    transaction_open as tx_open,
    transaction_query as tx_query,
    transaction_commit as tx_commit,
    transaction_close as tx_close,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "TypeDB MCP Server",
    # description="Provides query capability against a TypeDB server"
)

@mcp.tool
def query(query: str, database: str, transaction_type: str) -> str:
    """Executes given TypeQL query against the given database.
    
    Args:
        query: TypeQL query to be executed
        database: The name of the database against which the query will be executed
        transaction_type: Transaction type - "read" (for fetching data), "write" (for inserting data), or "schema" (for modifying the schema)
    
    Returns:
        Query results as JSON string
    
    Example:
        query("match $p isa person; fetch { $p.* };", "social_network")
    """
    return execute_query(query, database, transaction_type)


@mcp.tool
def database_list() -> str:
    """List all databases on the TypeDB server.
    
    Returns:
        JSON string containing list of databases
    """
    return db_list()


@mcp.tool
def database_create(name: str) -> str:
    """Create a new database on the TypeDB server.
    
    Args:
        name: Name of the database to create
    
    Returns:
        Success message
    """
    return db_create(name)


@mcp.tool
def database_delete(name: str) -> str:
    """Delete a database from the TypeDB server.
    
    Args:
        name: Name of the database to delete
    
    Returns:
        Success message
    """
    return db_delete(name)


@mcp.tool
def database_schema(name: str) -> str:
    """Get the complete database schema as TypeQL.
    
    Args:
        name: Name of the database
    
    Returns:
        Complete schema definition in TypeQL format (or empty string if no schema defined)
    """
    return db_schema(name)


@mcp.tool
def database_type_schema(name: str) -> str:
    """Get a database's type definitions.

    Args:
        name: Name of the database

    Returns:
        The type definitions in TypeQL format
    """
    return db_type_schema(name)


@mcp.tool
def transaction_open(database: str, transaction_type: str) -> str:
    """Open a multi-statement transaction and return its id.

    Use this instead of `query` when several statements must succeed or fail
    TOGETHER -- `query` commits each statement on its own, so a sequence of
    writes through it is not atomic.

    IMPORTANT: an open transaction pins its database (the database cannot be
    deleted while it is open). Every transaction you open must be finished
    with `transaction_commit` or `transaction_close`.

    Args:
        database: The database to open the transaction against
        transaction_type: "read", "write", or "schema"

    Returns:
        JSON containing the transactionId to pass to the other transaction tools
    """
    return tx_open(database, transaction_type)


@mcp.tool
def transaction_query(transaction_id: str, query: str) -> str:
    """Run a TypeQL statement inside an open transaction.

    Nothing is durable until `transaction_commit`.

    Args:
        transaction_id: Id returned by transaction_open
        query: TypeQL query to be executed

    Returns:
        Query results as JSON string
    """
    return tx_query(transaction_id, query)


@mcp.tool
def transaction_commit(transaction_id: str) -> str:
    """Commit every statement in the transaction, atomically, and end it.

    Args:
        transaction_id: Id returned by transaction_open

    Returns:
        Success message
    """
    return tx_commit(transaction_id)


@mcp.tool
def transaction_close(transaction_id: str) -> str:
    """End a transaction, DISCARDING any uncommitted writes.

    This is the rollback path -- TypeDB's HTTP API has no rollback endpoint.
    Closing an already-closed transaction is harmless.

    Args:
        transaction_id: Id returned by transaction_open

    Returns:
        Success message
    """
    return tx_close(transaction_id)


@mcp.tool
def user_list() -> str:
    """List all users on the TypeDB server.
    
    Returns:
        JSON string containing list of users
    """
    return usr_list()


@mcp.tool
def user_create(username: str, password: str) -> str:
    """Create a new user on the TypeDB server.
    
    Args:
        username: Username for the new user
        password: Password for the new user
    
    Returns:
        Success message
    """
    return usr_create(username, password)


@mcp.tool
def user_delete(username: str) -> str:
    """Delete a user from the TypeDB server.
    
    Args:
        username: Username of the user to delete
    
    Returns:
        Success message
    """
    return usr_delete(username)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TypeDB MCP Server")
    parser.add_argument("--port", type=int, default=8001, help="Port for the MCP server (default: 8001)")
    parser.add_argument("--transport", type=str, default="http", choices=["http", "stdio"], help="Transport mode: http (default) or stdio (for Claude Desktop)")
    # Credentials are read from the environment by default. Passing them on the
    # command line still works, but argv is world-readable via `ps`, so anyone
    # with a shell on this machine can read the password out of the process list.
    parser.add_argument("--typedb-address", type=str, default=os.environ.get("TYPEDB_ADDRESS"), help="Address for TypeDB's HTTP port (default: $TYPEDB_ADDRESS)")
    parser.add_argument("--typedb-username", type=str, default=os.environ.get("TYPEDB_USERNAME", "admin"), help="TypeDB username (default: $TYPEDB_USERNAME, else admin)")
    parser.add_argument("--typedb-password", type=str, default=os.environ.get("TYPEDB_PASSWORD", "password"), help="TypeDB password (default: $TYPEDB_PASSWORD, else password)")

    args = parser.parse_args()

    if not args.typedb_address:
        parser.error("--typedb-address is required (or set TYPEDB_ADDRESS)")

    if "--typedb-password" in sys.argv:
        logger.warning(
            "Password passed on the command line is visible to any process that "
            "can run `ps`. Prefer the TYPEDB_PASSWORD environment variable."
        )

    config.TYPEDB_URL = args.typedb_address
    config.TYPEDB_USERNAME = args.typedb_username
    config.TYPEDB_PASSWORD = args.typedb_password

    # Signal handler for graceful shutdown
    def handle_shutdown(signum, frame):
        logger.info("Received shutdown signal, initiating graceful shutdown...")

    # Register signal handlers
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    if args.transport == "stdio":
        logger.info(f"Starting TypeDB MCP Server in stdio mode")
        logger.info(f"Connecting to TypeDB at {args.typedb_address}")
        mcp.run(transport="stdio")
    else:
        logger.info(f"Starting TypeDB MCP Server on port {args.port}")
        logger.info(f"Connecting to TypeDB at {args.typedb_address}")
        mcp.run(transport="http", host="0.0.0.0", port=args.port)

