from __future__ import annotations

import json
from pathlib import Path

from folder_file.config import state_file


def _key(account: str, folder: str) -> str:
    return f"{account}::{folder}"


def load(path: Path | None = None) -> dict:
    p = path or state_file()
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict, path: Path | None = None) -> None:
    p = path or state_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    tmp.replace(p)


def get_entry(data: dict, account: str, folder: str) -> dict:
    return data.get(_key(account, folder), {"last_uid": 0, "counter": 1})


def update_entry(
    data: dict,
    account: str,
    folder: str,
    last_uid: int,
    counter: int,
) -> None:
    data[_key(account, folder)] = {"last_uid": int(last_uid), "counter": int(counter)}


def reset_entry(data: dict, account: str, folder: str) -> None:
    data.pop(_key(account, folder), None)
