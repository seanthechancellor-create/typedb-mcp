import requests
import config
from common import get_auth_token, handle_typedb_response


def list_databases() -> str:
    """Get all databases present on the server."""
    token = get_auth_token()
    response = requests.get(
        f"{config.TYPEDB_URL}/v1/databases",
        headers={"Authorization": f"Bearer {token}"}
    )
    handle_typedb_response(response)
    return response.text


def create_database(name: str) -> str:
    """Create a database on the server."""
    token = get_auth_token()
    response = requests.post(
        f"{config.TYPEDB_URL}/v1/databases/{name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    handle_typedb_response(response)
    return f"Database '{name}' created successfully"


def delete_database(name: str) -> str:
    """Delete a database from the server."""
    token = get_auth_token()
    response = requests.delete(
        f"{config.TYPEDB_URL}/v1/databases/{name}",
        headers={"Authorization": f"Bearer {token}"}
    )
    handle_typedb_response(response)
    return f"Database '{name}' deleted successfully"


def database_schema(name: str) -> str:
    """Get the complete database schema as TypeQL."""
    token = get_auth_token()
    response = requests.get(
        f"{config.TYPEDB_URL}/v1/databases/{name}/schema",
        headers={"Authorization": f"Bearer {token}"}
    )
    handle_typedb_response(response)
    return response.text


def database_type_schema(name: str) -> str:
    """Get the type definitions only.

    For a schema made purely of types this returns exactly what
    `database_schema` does -- verified against a live server. The two diverge
    only once a schema also carries non-type elements such as functions.
    """
    token = get_auth_token()
    response = requests.get(
        f"{config.TYPEDB_URL}/v1/databases/{name}/type-schema",
        headers={"Authorization": f"Bearer {token}"}
    )
    handle_typedb_response(response)
    return response.text
