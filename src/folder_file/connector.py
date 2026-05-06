from __future__ import annotations

import imaplib

from folder_file import accounts, imap_client
from folder_file.accounts import Account
from folder_file.oauth import gmail as gmail_oauth
from folder_file.oauth import microsoft as ms_oauth


def open_connection(account: Account) -> imaplib.IMAP4_SSL:
    if account.auth_type == "oauth":
        if account.provider == "gmail":
            token = gmail_oauth.get_fresh_access_token(account.id)
        elif account.provider == "microsoft":
            token = ms_oauth.get_fresh_access_token(account.id)
        else:
            raise RuntimeError(
                f"OAuth not supported for provider {account.provider!r}."
            )
        return imap_client.connect_xoauth2(
            account.imap_host, account.imap_port, account.email, token
        )

    secret = accounts.load_secret(account.id)
    if not secret or "password" not in secret:
        raise RuntimeError(
            f"No saved password for {account.id}. Reconnect the account."
        )
    return imap_client.connect(
        account.imap_host, account.imap_port, account.email, secret["password"]
    )
