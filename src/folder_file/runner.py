from __future__ import annotations

import imaplib
import sys
import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Optional

from folder_file import accounts as accounts_mod
from folder_file import imap_client, state
from folder_file.accounts import Account
from folder_file.connector import open_connection
from folder_file.downloader import extract_attachments, next_filename, save


@dataclass
class SweepParams:
    folder: str
    prefix: str
    allowed_exts: tuple[str, ...]
    output_dir: Path
    post_action: str = "leave"  # "leave" | "delete"


@dataclass
class SweepResult:
    saved: int = 0
    deleted: int = 0
    files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _format_subject(msg) -> str:
    raw = msg.get("Subject") or "(no subject)"
    return raw.replace("\r", " ").replace("\n", " ").strip()


def _format_date(msg) -> str:
    raw = msg.get("Date")
    if not raw:
        return "?"
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except Exception:
        return raw


def sweep_once(
    account: Account,
    params: SweepParams,
    log: Optional[Callable[[str], None]] = None,
) -> SweepResult:
    """Run a single sweep for an account/folder. Idempotent across runs via state file."""
    log = log or (lambda _msg: None)
    result = SweepResult()

    conn = open_connection(account)
    try:
        all_state = state.load()
        entry = state.get_entry(all_state, account.email, params.folder)
        last_uid = int(entry.get("last_uid", 0))
        counter = int(entry.get("counter", 1))
        new_last_uid = last_uid
        deleted_any = False

        for uid, msg in imap_client.iter_messages(conn, params.folder, since_uid=last_uid):
            new_last_uid = max(new_last_uid, uid)
            attachments = extract_attachments(msg, params.allowed_exts)
            if not attachments:
                continue

            subject = _format_subject(msg)
            date = _format_date(msg)
            for original_name, payload in attachments:
                fname = next_filename(params.prefix, counter, original_name)
                path = save(params.output_dir, fname, payload)
                log(f"  {path.name}  <- {subject!r} ({date})")
                result.files.append(str(path))
                counter += 1
                result.saved += 1

            if params.post_action == "delete":
                imap_client.delete_message(conn, uid)
                result.deleted += 1
                deleted_any = True

            state.update_entry(
                all_state, account.email, params.folder, new_last_uid, counter
            )
            state.save(all_state)

        if deleted_any:
            imap_client.expunge(conn)

        if new_last_uid != last_uid or counter != entry.get("counter", 1):
            state.update_entry(
                all_state, account.email, params.folder, new_last_uid, counter
            )
            state.save(all_state)
    finally:
        imap_client.logout(conn)

    return result


# --- CLI helpers (legacy interactive flow) ---


def run_once_cli(account: Account, params: SweepParams) -> None:
    print(f"\nScanning {params.folder} for new messages with attachments...")
    res = sweep_once(account, params, log=print)
    if res.saved == 0:
        print("No new attachments matched. State updated.")
    else:
        print(f"\nDone. {res.saved} file(s) saved to {params.output_dir}.")


def run_watch_cli(account: Account, params: SweepParams, interval_min: int) -> None:
    print(
        f"\nWatching {params.folder} every {interval_min} minute(s). "
        f"Press Ctrl+C to stop."
    )
    try:
        while True:
            try:
                res = sweep_once(account, params, log=print)
                if res.saved:
                    print(f"  ({res.saved} file(s) this sweep)")
                else:
                    print("  (no new attachments)")
            except imaplib.IMAP4.abort as e:
                print(f"  IMAP connection aborted: {e}. Will reconnect next sweep.")
            except imap_client.IMAPError as e:
                print(f"  IMAP error: {e}. Will retry next sweep.")
            time.sleep(interval_min * 60)
    except KeyboardInterrupt:
        print("\nStopped.")


def print_schedule_snippet(folder: str) -> None:
    py = sys.executable.replace("/", "\\")
    print()
    print("To run this on a schedule, paste one of the following:")
    print()
    print("Windows Task Scheduler (every 30 minutes):")
    print(
        f'  schtasks /create /sc minute /mo 30 /tn "folder_file_{folder.replace("/", "_")}" '
        f'/tr "\\"{py}\\" -m folder_file --auto"'
    )
    print()
    print("cron equivalent (Linux/macOS, every 30 minutes):")
    print(f"  */30 * * * * {py} -m folder_file --auto")
