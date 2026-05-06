from __future__ import annotations

import secrets
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from folder_file import __version__, accounts as accounts_mod
from folder_file import imap_client, jobs, state
from folder_file.accounts import Account, make_account_id
from folder_file.config import (
    COMMON_EXTENSIONS,
    DEFAULT_API_HOST,
    DEFAULT_API_PORT,
    PROVIDER_HINTS,
)
from folder_file.connector import open_connection
from folder_file.downloader import normalize_extensions
from folder_file.oauth import gmail as gmail_oauth
from folder_file.oauth import microsoft as ms_oauth
from folder_file.runner import SweepParams


# ---- in-memory pending OAuth flows ----

_pending_flows: dict[str, dict[str, Any]] = {}
_pending_lock = threading.Lock()
_FLOW_TTL_SEC = 600


def _stash_flow(state_key: str, payload: dict[str, Any]) -> None:
    with _pending_lock:
        _pending_flows[state_key] = {"payload": payload, "ts": time.time()}
        # garbage-collect old entries
        cutoff = time.time() - _FLOW_TTL_SEC
        for k in list(_pending_flows):
            if _pending_flows[k]["ts"] < cutoff:
                _pending_flows.pop(k, None)


def _pop_flow(state_key: str) -> dict[str, Any] | None:
    with _pending_lock:
        entry = _pending_flows.pop(state_key, None)
        return entry["payload"] if entry else None


# ---- request/response schemas ----


class PasswordAccountIn(BaseModel):
    email: str
    password: str
    imap_host: str | None = None
    imap_port: int = 993


class RunIn(BaseModel):
    account_id: str
    folder: str
    prefix: str = Field(min_length=1, max_length=64)
    allowed_exts: list[str] = Field(default_factory=list)
    output_dir: str
    post_action: str = "leave"


class HealthOut(BaseModel):
    ok: bool
    version: str


# ---- app ----


def create_app() -> FastAPI:
    app = FastAPI(title="folder_file", version=__version__)

    # Lovable apps run on *.lovable.app and lovable.dev. We allow them via regex,
    # plus standard localhost dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        r"|^https://([a-z0-9-]+\.)?lovable\.(app|dev)$"
        r"|^https://([a-z0-9-]+\.)?lovableproject\.com$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", response_model=HealthOut)
    def healthz() -> HealthOut:
        return HealthOut(ok=True, version=__version__)

    @app.get("/providers")
    def providers() -> dict:
        return {
            "common_extensions": COMMON_EXTENSIONS,
            "imap_hints": [
                {"domain": d, "host": h, "port": p}
                for d, (h, p) in PROVIDER_HINTS.items()
            ],
        }

    # ---- accounts ----

    @app.get("/accounts")
    def list_accounts() -> dict:
        return {"accounts": [a.public_dict() for a in accounts_mod.list_accounts()]}

    @app.delete("/accounts/{account_id}")
    def delete_account(account_id: str) -> dict:
        ok = accounts_mod.delete_account(account_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Account not found")
        return {"ok": True}

    @app.get("/accounts/{account_id}/folders")
    def list_folders(account_id: str) -> dict:
        account = accounts_mod.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        try:
            conn = open_connection(account)
        except Exception as e:
            raise HTTPException(status_code=502, detail=str(e))
        try:
            folders = imap_client.list_folders(conn)
        finally:
            imap_client.logout(conn)
        return {"folders": folders}

    @app.get("/accounts/{account_id}/state")
    def account_state(account_id: str) -> dict:
        account = accounts_mod.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        all_state = state.load()
        entries = {
            k: v
            for k, v in all_state.items()
            if k.startswith(f"{account.email}::")
        }
        return {"entries": entries}

    @app.post("/accounts/{account_id}/state/reset")
    def reset_state(account_id: str, folder: str = Query(...)) -> dict:
        account = accounts_mod.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        data = state.load()
        state.reset_entry(data, account.email, folder)
        state.save(data)
        return {"ok": True}

    # ---- password-based account creation ----

    @app.post("/accounts/password")
    def add_password_account(body: PasswordAccountIn) -> dict:
        host = body.imap_host
        port = body.imap_port
        if not host:
            hint = imap_client.guess_host(body.email)
            if not hint:
                raise HTTPException(
                    status_code=400,
                    detail="imap_host is required (could not auto-detect from email domain).",
                )
            host, port = hint

        try:
            conn = imap_client.connect(host, port, body.email, body.password)
            imap_client.logout(conn)
        except imap_client.IMAPError as e:
            raise HTTPException(status_code=401, detail=str(e))

        account = Account(
            id=make_account_id("imap", body.email),
            provider="imap",
            email=body.email,
            imap_host=host,
            imap_port=port,
            auth_type="password",
        )
        accounts_mod.upsert_account(account)
        accounts_mod.store_secret(account.id, {"password": body.password})
        return account.public_dict()

    # ---- Gmail OAuth ----

    @app.post("/auth/gmail/start")
    def gmail_start() -> dict:
        try:
            auth_url, state_key, flow = gmail_oauth.start_authorization()
        except gmail_oauth.OAuthConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        _stash_flow(state_key, {"provider": "gmail", "flow": flow})
        return {"auth_url": auth_url, "state": state_key}

    @app.get("/auth/gmail/callback", response_class=HTMLResponse)
    def gmail_callback(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
    ):
        if error:
            return HTMLResponse(_callback_html(False, f"Google returned error: {error}"))
        if not code or not state:
            return HTMLResponse(_callback_html(False, "Missing code or state."))
        payload = _pop_flow(state)
        if not payload:
            return HTMLResponse(_callback_html(False, "Auth state expired or unknown."))

        flow = payload["flow"]
        full_url = (
            f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}/auth/gmail/callback?"
            + urlencode({"code": code, "state": state})
        )
        try:
            tokens = gmail_oauth.complete_authorization(flow, full_url)
        except Exception as e:
            return HTMLResponse(_callback_html(False, f"Token exchange failed: {e}"))

        account = Account(
            id=make_account_id("gmail", tokens["email"]),
            provider="gmail",
            email=tokens["email"],
            imap_host="imap.gmail.com",
            imap_port=993,
            auth_type="oauth",
        )
        accounts_mod.upsert_account(account)
        accounts_mod.store_secret(
            account.id,
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": tokens["expires_at"],
            },
        )
        return HTMLResponse(_callback_html(True, f"Connected {tokens['email']}"))

    # ---- Microsoft OAuth ----

    @app.post("/auth/microsoft/start")
    def ms_start() -> dict:
        try:
            auth_url, flow = ms_oauth.start_authorization()
        except gmail_oauth.OAuthConfigError as e:
            raise HTTPException(status_code=400, detail=str(e))
        state_key = flow.get("state") or secrets.token_urlsafe(16)
        _stash_flow(state_key, {"provider": "microsoft", "flow": flow})
        return {"auth_url": auth_url, "state": state_key}

    @app.get("/auth/microsoft/callback", response_class=HTMLResponse)
    def ms_callback(
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ):
        if error:
            return HTMLResponse(
                _callback_html(False, f"Microsoft returned error: {error}: {error_description}")
            )
        if not code or not state:
            return HTMLResponse(_callback_html(False, "Missing code or state."))
        payload = _pop_flow(state)
        if not payload:
            return HTMLResponse(_callback_html(False, "Auth state expired or unknown."))

        try:
            tokens = ms_oauth.complete_authorization(
                payload["flow"], {"code": code, "state": state}
            )
        except Exception as e:
            return HTMLResponse(_callback_html(False, f"Token exchange failed: {e}"))

        account = Account(
            id=make_account_id("microsoft", tokens["email"]),
            provider="microsoft",
            email=tokens["email"],
            imap_host="outlook.office365.com",
            imap_port=993,
            auth_type="oauth",
        )
        accounts_mod.upsert_account(account)
        accounts_mod.store_secret(
            account.id,
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": tokens["expires_at"],
            },
        )
        return HTMLResponse(_callback_html(True, f"Connected {tokens['email']}"))

    # ---- run / jobs ----

    @app.post("/run")
    def run_sweep(body: RunIn) -> dict:
        account = accounts_mod.get_account(body.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        out_dir = Path(body.output_dir).expanduser().resolve()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise HTTPException(
                status_code=400, detail=f"Cannot create output_dir: {e}"
            )

        params = SweepParams(
            folder=body.folder,
            prefix=body.prefix,
            allowed_exts=normalize_extensions(body.allowed_exts),
            output_dir=out_dir,
            post_action=body.post_action,
        )
        job = jobs.submit_sweep(account, params)
        return {"job_id": job.id}

    @app.get("/jobs")
    def list_jobs() -> dict:
        return {"jobs": [j.public_dict() for j in jobs.list_recent()]}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        j = jobs.get(job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        return j.public_dict()

    return app


def _callback_html(success: bool, message: str) -> str:
    title = "folder_file - connected" if success else "folder_file - error"
    color = "#16a34a" if success else "#dc2626"
    icon = "&#10003;" if success else "&#9888;"
    return f"""<!doctype html>
<html><head><title>{title}</title><meta charset="utf-8">
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif;
  display:flex; align-items:center; justify-content:center;
  min-height:100vh; margin:0; background:#f8fafc; color:#0f172a; }}
.card {{ background:white; padding:32px 40px; border-radius:12px;
  box-shadow:0 1px 3px rgba(0,0,0,0.08); max-width:480px; }}
.icon {{ font-size:40px; color:{color}; margin-bottom:8px; }}
h1 {{ font-size:18px; margin:0 0 8px 0; }}
p {{ margin:0; color:#475569; line-height:1.5; }}
.hint {{ margin-top:16px; font-size:13px; color:#94a3b8; }}
</style></head><body>
<div class="card">
  <div class="icon">{icon}</div>
  <h1>{message}</h1>
  <p>{'Account saved. You can close this tab and return to the app.' if success else 'Please try again from the app.'}</p>
  <p class="hint">folder_file local server</p>
</div></body></html>"""
