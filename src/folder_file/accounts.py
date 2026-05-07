from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import keyring

from folder_file.config import KEYRING_TOKEN_SERVICE, accounts_file, state_dir


@dataclass
class Account:
    id: str
    provider: str         # "gmail" | "microsoft" | "imap"
    email: str
    imap_host: str
    imap_port: int
    auth_type: str        # "oauth" | "password"
    display_name: Optional[str] = None
    extras: dict = field(default_factory=dict)

    def public_dict(self) -> dict:
        return asdict(self)


def _load_raw(path: Path | None = None) -> dict:
    p = path or accounts_file()
    if not p.exists():
        return {"accounts": []}
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"accounts": []}


def _save_raw(data: dict, path: Path | None = None) -> None:
    p = path or accounts_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    tmp.replace(p)


def list_accounts(path: Path | None = None) -> list[Account]:
    raw = _load_raw(path)
    return [Account(**a) for a in raw.get("accounts", [])]


def get_account(account_id: str, path: Path | None = None) -> Optional[Account]:
    for a in list_accounts(path):
        if a.id == account_id:
            return a
    return None


def upsert_account(account: Account, path: Path | None = None) -> None:
    raw = _load_raw(path)
    accts = [a for a in raw.get("accounts", []) if a.get("id") != account.id]
    accts.append(asdict(account))
    raw["accounts"] = accts
    _save_raw(raw, path)


def delete_account(account_id: str, path: Path | None = None) -> bool:
    raw = _load_raw(path)
    before = len(raw.get("accounts", []))
    raw["accounts"] = [a for a in raw.get("accounts", []) if a.get("id") != account_id]
    _save_raw(raw, path)
    try:
        _secret_path(account_id).unlink(missing_ok=True)
    except OSError:
        pass
    try:
        keyring.delete_password(KEYRING_TOKEN_SERVICE, account_id)
    except Exception:
        pass
    return len(raw["accounts"]) < before


def make_account_id(provider: str, email: str) -> str:
    return f"{provider}:{email.lower()}"


# --- secret blob (tokens or password) per account, file-backed ---
#
# Stored as JSON in %APPDATA%\folder_file\secrets\<sha256-of-account-id>.json
# (XDG equivalent on POSIX). The keyring approach we tried first hits the
# Windows Credential Manager 2.5KB blob ceiling — Microsoft's combined
# access+refresh token JSON exceeds it, so the value silently truncated.
# File-based storage has the same trust boundary (user-only access to %APPDATA%)
# without the size limit.


def _secret_dir() -> Path:
    p = state_dir() / "secrets"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _secret_path(account_id: str) -> Path:
    safe = hashlib.sha256(account_id.encode("utf-8")).hexdigest()
    return _secret_dir() / f"{safe}.json"


def store_secret(account_id: str, payload: dict) -> None:
    p = _secret_path(account_id)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    tmp.replace(p)


def load_secret(account_id: str) -> Optional[dict]:
    p = _secret_path(account_id)
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    # Fallback: read from legacy keyring storage if it's there (for installs
    # that connected accounts before the file-backed switch).
    raw = keyring.get_password(KEYRING_TOKEN_SERVICE, account_id)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    # Migrate forward so the next load skips the keyring branch.
    try:
        store_secret(account_id, data)
    except OSError:
        pass
    return data


def update_oauth_tokens(
    account_id: str,
    access_token: str,
    refresh_token: str | None,
    expires_at: float,
) -> None:
    secret = load_secret(account_id) or {}
    secret["access_token"] = access_token
    if refresh_token:
        secret["refresh_token"] = refresh_token
    secret["expires_at"] = expires_at
    store_secret(account_id, secret)


def is_token_expired(secret: dict, leeway_seconds: int = 60) -> bool:
    exp = secret.get("expires_at")
    if not exp:
        return True
    return time.time() + leeway_seconds >= float(exp)
