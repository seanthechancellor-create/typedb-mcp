"""Database introspection tools, against the real local server."""
from database import database_type_schema


def test_type_schema_lists_the_defined_types(scratch_db):
    result = database_type_schema(scratch_db)

    assert "widget" in result
    assert "tag" in result
