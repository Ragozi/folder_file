from __future__ import annotations

import time
from typing import Optional

import httpx
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from folder_file import accounts
from folder_file.config import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    GOOGLE_SCOPES,
    load_oauth_client_config,
)


class OAuthConfigError(RuntimeError):
    pass


def _redirect_uri() -> str:
    return f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}/auth/gmail/callback"


def _client_config() -> dict:
    cfg = load_oauth_client_config("google")
    if not cfg:
        raise OAuthConfigError(
            "Google OAuth client not configured. Set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET env vars, or add them to oauth_clients.json. "
            "See README for setup steps."
        )
    return {
        "installed": {
            "client_id": cfg["client_id"],
            "client_secret": cfg["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_redirect_uri()],
        }
    }


def build_flow() -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_SCOPES,
        redirect_uri=_redirect_uri(),
    )
    return flow


def start_authorization() -> tuple[str, str, Flow]:
    """Returns (auth_url, state, flow). Caller stashes flow under state for callback."""
    flow = build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url, state, flow


def complete_authorization(flow: Flow, full_callback_url: str) -> dict:
    flow.fetch_token(authorization_response=full_callback_url)
    creds: Credentials = flow.credentials
    email = _fetch_user_email(creds.token)
    expires_at = creds.expiry.timestamp() if creds.expiry else (time.time() + 3500)
    return {
        "email": email,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": expires_at,
    }


def _fetch_user_email(access_token: str) -> str:
    r = httpx.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10.0,
    )
    r.raise_for_status()
    data = r.json()
    email = data.get("email")
    if not email:
        raise RuntimeError("Google userinfo response did not include an email.")
    return email


def get_fresh_access_token(account_id: str) -> str:
    secret = accounts.load_secret(account_id)
    if not secret:
        raise RuntimeError(f"No saved tokens for {account_id}.")

    if not accounts.is_token_expired(secret):
        return secret["access_token"]

    refresh = secret.get("refresh_token")
    if not refresh:
        raise RuntimeError(
            f"Access token for {account_id} expired and no refresh token is saved. "
            "Reconnect the account."
        )

    cfg = load_oauth_client_config("google")
    if not cfg:
        raise OAuthConfigError("Google OAuth client not configured.")

    creds = Credentials(
        token=secret.get("access_token"),
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scopes=GOOGLE_SCOPES,
    )
    creds.refresh(GoogleRequest())

    expires_at = creds.expiry.timestamp() if creds.expiry else (time.time() + 3500)
    accounts.update_oauth_tokens(
        account_id=account_id,
        access_token=creds.token,
        refresh_token=creds.refresh_token or refresh,
        expires_at=expires_at,
    )
    return creds.token
