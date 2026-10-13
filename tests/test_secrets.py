"""Sır yönetimi testleri — spec §5.7 (B-16 regresyonu)."""
from __future__ import annotations

import json

import pytest

from app.security import secrets as sec


def test_backend_available_on_windows():
    assert sec.backend_available() is True


def test_set_get_delete_roundtrip():
    sec.set_secret("test_ultron_tmp", "gizli-deger-123")
    try:
        assert sec.get_secret("test_ultron_tmp") == "gizli-deger-123"
    finally:
        assert sec.delete_secret("test_ultron_tmp") is True
    assert sec.get_secret("test_ultron_tmp") is None


def test_migrate_legacy_moves_and_deletes(tmp_path):
    legacy = tmp_path / "api_keys.json"
    legacy.write_text(json.dumps({"gemini_api_key": "ANAHTAR-XYZ", "bos": ""}),
                      encoding="utf-8")
    moved = sec.migrate_legacy(legacy)
    try:
        assert "gemini_api_key" in moved
        assert not legacy.exists(), "legacy dosya silinmeli"
        assert sec.get_secret("gemini_api_key") == "ANAHTAR-XYZ"
    finally:
        sec.delete_secret("gemini_api_key")


def test_migrate_missing_file_ok(tmp_path):
    assert sec.migrate_legacy(tmp_path / "yok.json") == []


def test_no_plaintext_fallback():
    """keyring varken düz-metne düşme yolu yoktur: set her zaman keyring'e gider."""
    import inspect

    src = inspect.getsource(sec.set_secret)
    assert "write_text" not in src and "open(" not in src
