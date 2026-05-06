from __future__ import annotations

import getpass

import keyring

from folder_file.config import KEYRING_SERVICE

_LAST_USERNAME_KEY = "__last_username__"


def get_or_prompt() -> tuple[str, str]:
    username = keyring.get_password(KEYRING_SERVICE, _LAST_USERNAME_KEY)
    password = keyring.get_password(KEYRING_SERVICE, username) if username else None

    if username and password:
        print(f"Using saved credentials for {username}")
        confirm = input("Use a different account? [y/N]: ").strip().lower()
        if confirm != "y":
            return username, password

    return _prompt_and_store()


def _prompt_and_store() -> tuple[str, str]:
    username = input("Email address: ").strip()
    if not username:
        raise SystemExit("Email address is required.")
    password = getpass.getpass("App password: ")
    if not password:
        raise SystemExit("Password is required.")
    keyring.set_password(KEYRING_SERVICE, username, password)
    keyring.set_password(KEYRING_SERVICE, _LAST_USERNAME_KEY, username)
    print("Credentials saved to OS keyring.")
    return username, password


def clear(username: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, username)
    except keyring.errors.PasswordDeleteError:
        pass
    last = keyring.get_password(KEYRING_SERVICE, _LAST_USERNAME_KEY)
    if last == username:
        try:
            keyring.delete_password(KEYRING_SERVICE, _LAST_USERNAME_KEY)
        except keyring.errors.PasswordDeleteError:
            pass
