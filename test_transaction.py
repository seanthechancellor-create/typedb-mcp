"""Transaction tools, tested against a real local TypeDB server."""
import json

import pytest
import requests

from query import query as one_shot_query
from transaction import (
    transaction_close,
    transaction_commit,
    transaction_open,
    transaction_query,
)

COUNT = "match $x isa $t; reduce $c = count;"
COUNT_WIDGETS = "match $w isa widget; reduce $c = count;"


def _open(db, kind="read"):
    return json.loads(transaction_open(db, kind))["transactionId"]


def _widgets(db):
    """Count widgets in a FRESH transaction, so we see only durable state."""
    result = json.loads(one_shot_query(COUNT_WIDGETS, db, "read"))
    return result["answers"][0]["data"]["c"]["value"]


def test_open_returns_a_transaction_id(scratch_db):
    tx = _open(scratch_db)
    try:
        assert tx
    finally:
        transaction_close(tx)


def test_query_runs_inside_an_open_transaction(scratch_db):
    tx = _open(scratch_db)
    try:
        result = json.loads(transaction_query(tx, COUNT))

        assert result["answers"][0]["data"]["c"]["value"] == 0
    finally:
        transaction_close(tx)


def test_close_invalidates_the_transaction(scratch_db):
    """Close is idempotent, so the real proof is that the id stops working."""
    tx = _open(scratch_db)
    transaction_query(tx, COUNT)  # usable while open

    transaction_close(tx)

    with pytest.raises(requests.HTTPError):
        transaction_query(tx, COUNT)


def test_commit_makes_writes_durable(scratch_db):
    tx = _open(scratch_db, "write")
    transaction_query(tx, 'insert $w isa widget, has tag "kept";')

    transaction_commit(tx)

    assert _widgets(scratch_db) == 1


def test_close_discards_uncommitted_writes(scratch_db):
    """The whole point of explicit transactions: an abandoned write vanishes."""
    tx = _open(scratch_db, "write")
    transaction_query(tx, 'insert $w isa widget, has tag "dropped";')

    transaction_close(tx)

    assert _widgets(scratch_db) == 0


def test_two_writes_commit_together(scratch_db):
    """Both statements share one transaction, so one commit lands both."""
    tx = _open(scratch_db, "write")
    transaction_query(tx, 'insert $w isa widget, has tag "first";')
    transaction_query(tx, 'insert $w isa widget, has tag "second";')

    transaction_commit(tx)

    assert _widgets(scratch_db) == 2
