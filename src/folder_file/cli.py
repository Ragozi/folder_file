from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

import keyring
import questionary

from folder_file import accounts as accounts_mod
from folder_file import imap_client, runner
from folder_file.accounts import Account, make_account_id
from folder_file.config import COMMON_EXTENSIONS, KEYRING_SERVICE
from folder_file.downloader import normalize_extensions
from folder_file.runner import SweepParams

PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,63}$")
_LAST_USERNAME_KEY = "__last_username__"


def _get_or_prompt_password_account() -> tuple[Account, str]:
    """Legacy interactive credential flow: prompts for email + app password."""
    last = keyring.get_password(KEYRING_SERVICE, _LAST_USERNAME_KEY)
    if last:
        saved = keyring.get_password(KEYRING_SERVICE, last)
        if saved:
            print(f"Using saved credentials for {last}")
            again = input("Use a different account? [y/N]: ").strip().lower()
            if again != "y":
                return _account_from_password(last, saved), saved

    username = input("Email address: ").strip()
    if not username:
        raise SystemExit("Email address is required.")
    password = getpass.getpass("App password: ")
    if not password:
        raise SystemExit("Password is required.")

    keyring.set_password(KEYRING_SERVICE, username, password)
    keyring.set_password(KEYRING_SERVICE, _LAST_USERNAME_KEY, username)
    print("Credentials saved to OS keyring.")
    return _account_from_password(username, password), password


def _account_from_password(email: str, password: str) -> Account:
    hint = imap_client.guess_host(email)
    host, port = hint or ("", 993)
    if not host:
        host = questionary.text("IMAP host:").ask() or ""
        if not host:
            raise SystemExit("IMAP host is required.")
        port_raw = questionary.text("IMAP port:", default="993").ask()
        try:
            port = int((port_raw or "993").strip())
        except ValueError:
            port = 993
    account = Account(
        id=make_account_id("imap", email),
        provider="imap",
        email=email,
        imap_host=host,
        imap_port=port,
        auth_type="password",
    )
    accounts_mod.upsert_account(account)
    accounts_mod.store_secret(account.id, {"password": password})
    return account


def _ask_prefix() -> str:
    while True:
        prefix = questionary.text(
            "Naming prefix (e.g. 'Aria' -> Aria_001.jpg):"
        ).ask()
        if prefix is None:
            raise SystemExit("Cancelled.")
        prefix = prefix.strip()
        if PREFIX_RE.match(prefix):
            return prefix
        print(
            "  Invalid prefix. Use letters, digits, underscore or hyphen only "
            "(must start with a letter or digit)."
        )


def _ask_extensions() -> tuple[str, ...]:
    choices = [questionary.Choice(ext, value=ext) for ext in COMMON_EXTENSIONS]
    choices.append(questionary.Choice("Other... (enter custom list)", value="__other__"))
    selected = questionary.checkbox(
        "File types to download (space to toggle, enter to confirm):",
        choices=choices,
    ).ask()
    if selected is None:
        raise SystemExit("Cancelled.")

    exts: list[str] = [s for s in selected if s != "__other__"]
    if "__other__" in selected:
        custom = questionary.text(
            "Custom extensions, comma-separated (e.g. '.eml,.csv,heic'):"
        ).ask()
        if custom:
            for piece in custom.split(","):
                exts.append(piece)

    if not exts:
        print("  No extensions selected — defaulting to ALL attachments.")
    return normalize_extensions(exts)


def _ask_output_dir(prefix: str) -> Path:
    default = str(Path.home() / "Downloads" / prefix)
    raw = questionary.text("Output folder:", default=default).ask()
    if raw is None:
        raise SystemExit("Cancelled.")
    p = Path(raw).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ask_post_action() -> str:
    return questionary.select(
        "After downloading, what should happen to the email?",
        choices=[
            questionary.Choice("Leave it alone (recommended)", value="leave"),
            questionary.Choice("Delete it from the server", value="delete"),
        ],
    ).ask() or "leave"


def _ask_run_mode() -> tuple[str, int]:
    mode = questionary.select(
        "Run mode:",
        choices=[
            questionary.Choice("Once - single sweep, then exit", value="once"),
            questionary.Choice("Watch - keep polling every N minutes", value="watch"),
            questionary.Choice("Schedule - print a cron/schtasks line and exit", value="schedule"),
        ],
    ).ask() or "once"

    interval = 5
    if mode == "watch":
        raw = questionary.text("Polling interval in minutes:", default="5").ask()
        try:
            interval = max(1, int((raw or "5").strip()))
        except ValueError:
            interval = 5
    return mode, interval


def main() -> None:
    print("folder_file - IMAP attachment downloader")
    print("-" * 42)
    print("(For OAuth + UI, run: python -m folder_file.server)")
    print()

    account, _password = _get_or_prompt_password_account()

    print(f"Connecting to {account.imap_host}:{account.imap_port}...")
    try:
        from folder_file.connector import open_connection
        conn = open_connection(account)
    except Exception as e:
        print(f"\n{e}")
        sys.exit(1)

    try:
        folders = imap_client.list_folders(conn)
    finally:
        imap_client.logout(conn)

    if not folders:
        print("No folders found on the server.")
        sys.exit(1)

    folder = questionary.select(
        "Pick a folder to scan:",
        choices=[questionary.Choice(f, value=f) for f in folders],
    ).ask()
    if folder is None:
        raise SystemExit("Cancelled.")

    prefix = _ask_prefix()
    allowed_exts = _ask_extensions()
    output_dir = _ask_output_dir(prefix)
    post_action = _ask_post_action()
    run_mode, interval = _ask_run_mode()

    params = SweepParams(
        folder=folder,
        prefix=prefix,
        allowed_exts=allowed_exts,
        output_dir=output_dir,
        post_action=post_action,
    )

    print()
    print(f"  account     : {account.email}")
    print(f"  folder      : {params.folder}")
    print(f"  prefix      : {params.prefix}")
    print(f"  extensions  : {', '.join(params.allowed_exts) or '(all)'}")
    print(f"  output      : {params.output_dir}")
    print(f"  post-action : {params.post_action}")
    print(f"  run mode    : {run_mode}" + (f" (every {interval}m)" if run_mode == "watch" else ""))

    if run_mode == "schedule":
        runner.print_schedule_snippet(params.folder)
        return
    if run_mode == "watch":
        runner.run_watch_cli(account, params, interval)
        return
    runner.run_once_cli(account, params)
