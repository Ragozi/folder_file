from __future__ import annotations

from pathlib import Path

from folder_file import state


def test_load_missing_returns_empty(tmp_path: Path):
    assert state.load(tmp_path / "missing.json") == {}


def test_round_trip_preserves_counter(tmp_path: Path):
    p = tmp_path / "state.json"
    data: dict = {}
    state.update_entry(data, "user@example.com", "INBOX/Aria", last_uid=42, counter=8)
    state.save(data, p)

    reloaded = state.load(p)
    entry = state.get_entry(reloaded, "user@example.com", "INBOX/Aria")
    assert entry == {"last_uid": 42, "counter": 8}


def test_separate_folders_keep_separate_counters(tmp_path: Path):
    data: dict = {}
    state.update_entry(data, "u@e.com", "INBOX/A", last_uid=10, counter=5)
    state.update_entry(data, "u@e.com", "INBOX/B", last_uid=99, counter=120)

    assert state.get_entry(data, "u@e.com", "INBOX/A") == {"last_uid": 10, "counter": 5}
    assert state.get_entry(data, "u@e.com", "INBOX/B") == {"last_uid": 99, "counter": 120}


def test_separate_accounts_keep_separate_counters(tmp_path: Path):
    data: dict = {}
    state.update_entry(data, "alice@e.com", "INBOX", last_uid=1, counter=3)
    state.update_entry(data, "bob@e.com", "INBOX", last_uid=7, counter=11)

    assert state.get_entry(data, "alice@e.com", "INBOX") == {"last_uid": 1, "counter": 3}
    assert state.get_entry(data, "bob@e.com", "INBOX") == {"last_uid": 7, "counter": 11}


def test_get_entry_default_when_missing():
    assert state.get_entry({}, "x@y.z", "INBOX") == {"last_uid": 0, "counter": 1}


def test_reset_entry(tmp_path: Path):
    data: dict = {}
    state.update_entry(data, "u@e.com", "INBOX", last_uid=10, counter=5)
    state.reset_entry(data, "u@e.com", "INBOX")
    assert state.get_entry(data, "u@e.com", "INBOX") == {"last_uid": 0, "counter": 1}


def test_save_is_atomic_via_tmp(tmp_path: Path, monkeypatch):
    p = tmp_path / "state.json"
    data: dict = {}
    state.update_entry(data, "u@e.com", "INBOX", last_uid=1, counter=2)
    state.save(data, p)
    assert p.exists()
    assert not (tmp_path / "state.json.tmp").exists()
