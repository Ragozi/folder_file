from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from folder_file import accounts as accounts_mod
from folder_file.api import create_app


@pytest.fixture
def isolated_state(tmp_path: Path, monkeypatch):
    """Redirect state_dir() to a tmp dir and use an in-memory keyring backend."""
    monkeypatch.setattr("folder_file.config.state_dir", lambda: tmp_path)
    monkeypatch.setattr("folder_file.config.state_file", lambda: tmp_path / "state.json")
    monkeypatch.setattr("folder_file.config.accounts_file", lambda: tmp_path / "accounts.json")
    monkeypatch.setattr(
        "folder_file.config.oauth_clients_file", lambda: tmp_path / "oauth_clients.json"
    )

    import keyring
    import keyring.backend

    class _MemBackend(keyring.backend.KeyringBackend):
        priority = 1

        def __init__(self):
            self._store: dict[tuple[str, str], str] = {}

        def get_password(self, service, username):
            return self._store.get((service, username))

        def set_password(self, service, username, password):
            self._store[(service, username)] = password

        def delete_password(self, service, username):
            self._store.pop((service, username), None)

    prev = keyring.get_keyring()
    keyring.set_keyring(_MemBackend())
    yield tmp_path
    keyring.set_keyring(prev)


@pytest.fixture
def client(isolated_state) -> TestClient:
    return TestClient(create_app())


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "version" in body


def test_providers_returns_extensions_and_hints(client):
    r = client.get("/providers")
    assert r.status_code == 200
    body = r.json()
    assert ".pdf" in body["common_extensions"]
    domains = {h["domain"] for h in body["imap_hints"]}
    assert "gmail.com" in domains
    assert "outlook.com" in domains


def test_accounts_starts_empty(client):
    r = client.get("/accounts")
    assert r.status_code == 200
    assert r.json() == {"accounts": []}


def test_delete_missing_account_returns_404(client):
    r = client.delete("/accounts/gmail:nope@example.com")
    assert r.status_code == 404


def test_password_account_requires_reachable_imap(client):
    r = client.post(
        "/accounts/password",
        json={
            "email": "x@unknown-domain-xyz.test",
            "password": "p",
        },
    )
    # No host, no hint → 400
    assert r.status_code == 400


def test_run_rejects_missing_account(client):
    r = client.post(
        "/run",
        json={
            "account_id": "gmail:missing@example.com",
            "folder": "INBOX",
            "prefix": "Test",
            "allowed_exts": [".pdf"],
            "output_dir": str(Path.cwd() / "_does_not_matter"),
        },
    )
    assert r.status_code == 404


def test_jobs_starts_empty(client):
    r = client.get("/jobs")
    assert r.status_code == 200
    assert r.json() == {"jobs": []}


def test_oauth_start_requires_client_config(client):
    r = client.post("/auth/gmail/start")
    # No GOOGLE_CLIENT_ID/SECRET configured in test env → 400
    assert r.status_code == 400
    assert "Google OAuth client not configured" in r.json()["detail"]


def test_microsoft_oauth_start_requires_client_config(client):
    r = client.post("/auth/microsoft/start")
    assert r.status_code == 400
    assert "Microsoft OAuth client not configured" in r.json()["detail"]


def test_cors_allows_lovable_origin(client):
    r = client.options(
        "/healthz",
        headers={
            "Origin": "https://my-app.lovable.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    # FastAPI/Starlette CORS responds 200 OK to preflight
    assert r.status_code in (200, 204)
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}
