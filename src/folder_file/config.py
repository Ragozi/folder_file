from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "folder_file"
KEYRING_SERVICE = "folder_file"
KEYRING_TOKEN_SERVICE = "folder_file:tokens"

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8765

GOOGLE_SCOPES = [
    "https://mail.google.com/",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]
MICROSOFT_SCOPES = [
    "https://outlook.office.com/IMAP.AccessAsUser.All",
    "offline_access",
]
MICROSOFT_AUTHORITY = "https://login.microsoftonline.com/common"

COMMON_EXTENSIONS = [
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".heic",
    ".gif",
    ".webp",
    ".docx",
    ".xlsx",
    ".pptx",
    ".zip",
    ".csv",
    ".txt",
]

PROVIDER_HINTS = {
    "gmail.com": ("imap.gmail.com", 993),
    "googlemail.com": ("imap.gmail.com", 993),
    "outlook.com": ("outlook.office365.com", 993),
    "hotmail.com": ("outlook.office365.com", 993),
    "live.com": ("outlook.office365.com", 993),
    "msn.com": ("outlook.office365.com", 993),
    "icloud.com": ("imap.mail.me.com", 993),
    "me.com": ("imap.mail.me.com", 993),
    "yahoo.com": ("imap.mail.yahoo.com", 993),
    "fastmail.com": ("imap.fastmail.com", 993),
}


def state_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_file() -> Path:
    return state_dir() / "state.json"


def accounts_file() -> Path:
    return state_dir() / "accounts.json"


def oauth_clients_file() -> Path:
    return state_dir() / "oauth_clients.json"


def load_oauth_client_config(provider: str) -> dict | None:
    """Read OAuth client credentials. Provider is 'google' or 'microsoft'.
    Order: env vars first, then oauth_clients.json."""
    if provider == "google":
        cid = os.environ.get("GOOGLE_CLIENT_ID")
        secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        if cid and secret:
            return {"client_id": cid, "client_secret": secret}
    elif provider == "microsoft":
        cid = os.environ.get("MICROSOFT_CLIENT_ID")
        if cid:
            return {"client_id": cid}

    p = oauth_clients_file()
    if not p.exists():
        return None
    try:
        import json
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(provider)
    except (OSError, ValueError):
        return None


@dataclass
class RunConfig:
    username: str
    host: str
    port: int
    folder: str
    prefix: str
    allowed_exts: tuple[str, ...]
    output_dir: Path
    post_action: str          # "leave" | "delete"
    run_mode: str             # "once" | "watch" | "schedule"
    watch_interval_min: int = 5
    extras: dict = field(default_factory=dict)
