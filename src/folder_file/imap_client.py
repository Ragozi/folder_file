from __future__ import annotations

import email
import imaplib
import re
from email.message import Message
from typing import Iterator

from folder_file.config import PROVIDER_HINTS


class IMAPError(RuntimeError):
    pass


def guess_host(username: str) -> tuple[str, int] | None:
    if "@" not in username:
        return None
    domain = username.rsplit("@", 1)[1].lower()
    return PROVIDER_HINTS.get(domain)


def connect(host: str, port: int, username: str, password: str) -> imaplib.IMAP4_SSL:
    try:
        conn = imaplib.IMAP4_SSL(host, port)
    except OSError as e:
        raise IMAPError(f"Could not reach {host}:{port} — {e}") from e
    try:
        conn.login(username, password)
    except imaplib.IMAP4.error as e:
        raise IMAPError(
            f"Login failed for {username}. If using Gmail/Outlook, make sure you generated an app password. ({e})"
        ) from e
    return conn


def connect_xoauth2(
    host: str, port: int, username: str, access_token: str
) -> imaplib.IMAP4_SSL:
    try:
        conn = imaplib.IMAP4_SSL(host, port)
    except OSError as e:
        raise IMAPError(f"Could not reach {host}:{port} — {e}") from e
    sasl = f"user={username}\x01auth=Bearer {access_token}\x01\x01".encode("utf-8")
    try:
        conn.authenticate("XOAUTH2", lambda _challenge: sasl)
    except imaplib.IMAP4.error as e:
        raise IMAPError(
            f"XOAUTH2 login failed for {username}. The access token may have insufficient "
            f"scope or the IMAP service is disabled for this tenant. ({e})"
        ) from e
    return conn


_LIST_RE = re.compile(rb'\((?P<flags>[^)]*)\) "(?P<delim>[^"]+)" (?P<name>.+)$')


def list_folders(conn: imaplib.IMAP4_SSL) -> list[str]:
    typ, data = conn.list()
    if typ != "OK":
        raise IMAPError(f"LIST failed: {typ}")
    out: list[str] = []
    for raw in data:
        if raw is None:
            continue
        if isinstance(raw, tuple):
            raw = b" ".join(p for p in raw if isinstance(p, (bytes, bytearray)))
        m = _LIST_RE.match(raw)
        if not m:
            continue
        flags = m.group("flags").decode(errors="replace")
        if "\\Noselect" in flags:
            continue
        name_raw = m.group("name").strip()
        if name_raw.startswith(b'"') and name_raw.endswith(b'"'):
            name_raw = name_raw[1:-1]
        name = name_raw.decode("utf-8", errors="replace")
        out.append(name)
    out.sort(key=lambda s: (s != "INBOX", s.lower()))
    return out


def select_folder(conn: imaplib.IMAP4_SSL, folder: str) -> int:
    quoted = f'"{folder}"' if " " in folder or "/" in folder else folder
    typ, data = conn.select(quoted, readonly=False)
    if typ != "OK":
        raise IMAPError(f"Could not select folder {folder!r}: {data!r}")
    try:
        return int(data[0])
    except (ValueError, IndexError):
        return 0


def iter_messages(
    conn: imaplib.IMAP4_SSL,
    folder: str,
    since_uid: int = 0,
) -> Iterator[tuple[int, Message]]:
    select_folder(conn, folder)
    search_arg = f"{since_uid + 1}:*"
    typ, data = conn.uid("SEARCH", None, "UID", search_arg)
    if typ != "OK":
        raise IMAPError(f"UID SEARCH failed: {data!r}")
    raw_ids = data[0].split() if data and data[0] else []
    uids = sorted({int(x) for x in raw_ids if x.isdigit()})
    uids = [u for u in uids if u > since_uid]

    for uid in uids:
        typ, msg_data = conn.uid("FETCH", str(uid).encode(), "(RFC822)")
        if typ != "OK" or not msg_data or not msg_data[0]:
            continue
        payload = None
        for part in msg_data:
            if isinstance(part, tuple) and len(part) >= 2:
                payload = part[1]
                break
        if not payload:
            continue
        try:
            msg = email.message_from_bytes(payload)
        except Exception:
            continue
        yield uid, msg


def delete_message(conn: imaplib.IMAP4_SSL, uid: int) -> None:
    conn.uid("STORE", str(uid).encode(), "+FLAGS", "(\\Deleted)")


def expunge(conn: imaplib.IMAP4_SSL) -> None:
    conn.expunge()


def logout(conn: imaplib.IMAP4_SSL) -> None:
    try:
        conn.close()
    except Exception:
        pass
    try:
        conn.logout()
    except Exception:
        pass
