import base64
import binascii
import time

import requests
import config
import json

# Cached bearer token. Every tool call used to cost a full signin round-trip;
# the token is a JWT valid for well over an hour, so it is reused until it is
# close to expiring. Keyed on the connection identity so that repointing the
# server at a different host or user cannot serve a stale token.
_TOKEN_CACHE = {}

# Refresh this many seconds before the token actually expires, so a request
# cannot be issued with a token that dies in flight.
_EXPIRY_MARGIN_SECONDS = 60

# Used only when a token carries no readable `exp` claim.
_FALLBACK_LIFETIME_SECONDS = 60


def _token_expiry(token: str) -> float:
    """Read the `exp` claim out of a JWT. Returns a conservative fallback if
    the token is not a readable JWT -- never trust an unparseable token for
    longer than the fallback."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)  # restore stripped base64 padding
        return float(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except (IndexError, ValueError, KeyError, TypeError, binascii.Error):
        return time.time() + _FALLBACK_LIFETIME_SECONDS


def get_auth_token() -> str:
    """Sign in to TypeDB and get an access token, reusing a cached one."""
    identity = (config.TYPEDB_URL, config.TYPEDB_USERNAME)
    if (
        _TOKEN_CACHE.get("identity") == identity
        and time.time() < _TOKEN_CACHE.get("expires_at", 0)
    ):
        return _TOKEN_CACHE["token"]

    response = requests.post(
        f"{config.TYPEDB_URL}/v1/signin",
        json={"username": config.TYPEDB_USERNAME, "password": config.TYPEDB_PASSWORD}
    )
    handle_typedb_response(response)
    token = response.json()["token"]

    _TOKEN_CACHE["identity"] = identity
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = _token_expiry(token) - _EXPIRY_MARGIN_SECONDS
    return token


def handle_typedb_response(response: requests.Response) -> None:
    """Check response status and raise an error with TypeDB error details if needed.
    
    This ensures that TypeDB error messages are properly extracted from the response
    and propagated to the MCP client.
    
    Args:
        response: The requests.Response object to check
        
    Raises:
        requests.HTTPError: If the response status indicates an error, with TypeDB error details included
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Try to extract error details from TypeDB response
        error_data = response.json()
        http_error = requests.HTTPError(error_data, response=response)
        raise http_error from e
