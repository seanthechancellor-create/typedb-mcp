"""Explicit multi-statement transactions over the TypeDB HTTP API.

The one-shot `query` tool commits each statement on its own, so a sequence of
writes through it is not atomic. These wrap /v1/transactions/* so several
statements can share one transaction and commit or discard together.

NOTE: the HTTP API has no rollback endpoint. Closing without committing IS the
discard path -- that is why `transaction_close` documents itself that way.
"""
import requests

import config
from common import get_auth_token, handle_typedb_response


def transaction_open(database: str, transaction_type: str = "read") -> str:
    """Open a transaction and return its id as JSON."""
    token = get_auth_token()
    response = requests.post(
        f"{config.TYPEDB_URL}/v1/transactions/open",
        headers={"Authorization": f"Bearer {token}"},
        json={"databaseName": database, "transactionType": transaction_type},
    )
    handle_typedb_response(response)
    return response.text


def transaction_query(transaction_id: str, query: str) -> str:
    """Run a TypeQL statement inside an already-open transaction.

    Nothing is committed here. Writes become durable only on
    `transaction_commit`, so several statements can succeed or fail together.
    """
    token = get_auth_token()
    response = requests.post(
        f"{config.TYPEDB_URL}/v1/transactions/{transaction_id}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query},
    )
    handle_typedb_response(response)
    return response.text


def transaction_commit(transaction_id: str) -> str:
    """Commit every statement run in this transaction, atomically.

    Ends the transaction: the id is not reusable afterwards.
    """
    token = get_auth_token()
    response = requests.post(
        f"{config.TYPEDB_URL}/v1/transactions/{transaction_id}/commit",
        headers={"Authorization": f"Bearer {token}"},
    )
    handle_typedb_response(response)
    return f"Transaction '{transaction_id}' committed"


def transaction_close(transaction_id: str) -> str:
    """End a transaction, DISCARDING any uncommitted writes.

    This is the rollback path -- the HTTP API exposes no rollback endpoint.
    An open transaction pins its database (it cannot be deleted), so every
    opened transaction must reach close or commit.
    """
    token = get_auth_token()
    response = requests.post(
        f"{config.TYPEDB_URL}/v1/transactions/{transaction_id}/close",
        headers={"Authorization": f"Bearer {token}"},
    )
    handle_typedb_response(response)
    return f"Transaction '{transaction_id}' closed (uncommitted writes discarded)"
