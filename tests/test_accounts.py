from __future__ import annotations

from pathlib import Path

from folder_file import accounts as accounts_mod
from folder_file.accounts import Account, make_account_id


def test_make_account_id_lowercases_email():
    assert make_account_id("gmail", "Eric@Gmail.com") == "gmail:eric@gmail.com"


def test_upsert_and_list_round_trip(tmp_path: Path):
    p = tmp_path / "accounts.json"
    a = Account(
        id="gmail:e@g.com",
        provider="gmail",
        email="e@g.com",
        imap_host="imap.gmail.com",
        imap_port=993,
        auth_type="oauth",
    )
    accounts_mod.upsert_account(a, path=p)
    listed = accounts_mod.list_accounts(path=p)
    assert len(listed) == 1
    assert listed[0].email == "e@g.com"
    assert listed[0].provider == "gmail"


def test_upsert_replaces_existing(tmp_path: Path):
    p = tmp_path / "accounts.json"
    a1 = Account(
        id="gmail:e@g.com",
        provider="gmail",
        email="e@g.com",
        imap_host="imap.gmail.com",
        imap_port=993,
        auth_type="oauth",
        display_name="old",
    )
    a2 = Account(
        id="gmail:e@g.com",
        provider="gmail",
        email="e@g.com",
        imap_host="imap.gmail.com",
        imap_port=993,
        auth_type="oauth",
        display_name="new",
    )
    accounts_mod.upsert_account(a1, path=p)
    accounts_mod.upsert_account(a2, path=p)
    listed = accounts_mod.list_accounts(path=p)
    assert len(listed) == 1
    assert listed[0].display_name == "new"


def test_get_account_returns_none_when_missing(tmp_path: Path):
    p = tmp_path / "accounts.json"
    assert accounts_mod.get_account("gmail:nope@x.com", path=p) is None


def test_is_token_expired_handles_missing_field():
    assert accounts_mod.is_token_expired({}) is True


def test_is_token_expired_respects_leeway():
    import time
    fresh = {"expires_at": time.time() + 3600}
    assert accounts_mod.is_token_expired(fresh) is False
    stale = {"expires_at": time.time() - 1}
    assert accounts_mod.is_token_expired(stale) is True
    edge = {"expires_at": time.time() + 30}
    assert accounts_mod.is_token_expired(edge, leeway_seconds=60) is True
