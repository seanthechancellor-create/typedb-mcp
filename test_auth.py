"""Auth token caching, against the real local server."""
import requests

import common


def _count_signins(monkeypatch):
    """Wrap the real requests.post so signin round-trips are observable."""
    calls = []
    real_post = requests.post

    def counting_post(url, *args, **kwargs):
        if url.endswith("/v1/signin"):
            calls.append(url)
        return real_post(url, *args, **kwargs)

    monkeypatch.setattr(common.requests, "post", counting_post)
    return calls


def test_repeated_token_requests_sign_in_once(monkeypatch, _point_at_local_server):
    monkeypatch.setattr(common, "_TOKEN_CACHE", {})
    signins = _count_signins(monkeypatch)

    first = common.get_auth_token()
    second = common.get_auth_token()

    assert first == second
    assert len(signins) == 1


def test_expired_token_triggers_a_new_signin(monkeypatch, _point_at_local_server):
    monkeypatch.setattr(common, "_TOKEN_CACHE", {})
    signins = _count_signins(monkeypatch)
    common.get_auth_token()

    # Pretend the cached token has already expired.
    common._TOKEN_CACHE["expires_at"] = 0
    common.get_auth_token()

    assert len(signins) == 2
