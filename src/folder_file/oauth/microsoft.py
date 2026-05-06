from __future__ import annotations

import time
from typing import Any

import msal

from folder_file import accounts
from folder_file.config import (
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    MICROSOFT_AUTHORITY,
    MICROSOFT_SCOPES,
    load_oauth_client_config,
)
from folder_file.oauth.gmail import OAuthConfigError


def _redirect_uri() -> str:
    return f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}/auth/microsoft/callback"


def _build_app() -> msal.PublicClientApplication:
    cfg = load_oauth_client_config("microsoft")
    if not cfg:
        raise OAuthConfigError(
            "Microsoft OAuth client not configured. Set MICROSOFT_CLIENT_ID env var, "
            "or add it to oauth_clients.json. See README for setup steps."
        )
    return msal.PublicClientApplication(
        client_id=cfg["client_id"],
        authority=MICROSOFT_AUTHORITY,
    )


def start_authorization() -> tuple[str, dict]:
    """Returns (auth_url, flow_state). Caller stashes flow_state by its 'state' for callback."""
    app = _build_app()
    flow = app.initiate_auth_code_flow(
        scopes=MICROSOFT_SCOPES,
        redirect_uri=_redirect_uri(),
    )
    if "auth_uri" not in flow:
        raise RuntimeError(f"Microsoft auth flow init failed: {flow}")
    return flow["auth_uri"], flow


def complete_authorization(flow_state: dict, query_params: dict[str, Any]) -> dict:
    app = _build_app()
    result = app.acquire_token_by_auth_code_flow(flow_state, query_params)

    if "error" in result:
        raise RuntimeError(
            f"Microsoft auth failed: {result.get('error')}: "
            f"{result.get('error_description', '')}"
        )

    id_claims = result.get("id_token_claims") or {}
    email = (
        id_claims.get("preferred_username")
        or id_claims.get("email")
        or id_claims.get("upn")
    )
    if not email:
        raise RuntimeError("Microsoft id_token did not include an email/upn claim.")

    expires_at = time.time() + int(result.get("expires_in", 3600))
    return {
        "email": email,
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "expires_at": expires_at,
    }


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

    app = _build_app()
    result = app.acquire_token_by_refresh_token(
        refresh_token=refresh,
        scopes=MICROSOFT_SCOPES,
    )
    if "error" in result:
        raise RuntimeError(
            f"Microsoft token refresh failed: {result.get('error')}: "
            f"{result.get('error_description', '')}"
        )

    expires_at = time.time() + int(result.get("expires_in", 3600))
    accounts.update_oauth_tokens(
        account_id=account_id,
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token") or refresh,
        expires_at=expires_at,
    )
    return result["access_token"]
