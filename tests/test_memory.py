"""Hafıza testleri — B-17 (atomik) + hassas bilgi reddi."""
from __future__ import annotations

import asyncio
import json

import app.memory.store as store
from app.tools.registry import REGISTRY

import app.tools.memory_tools  # noqa: F401  (araçları kaydet)


def _call(name, **args):
    return asyncio.run(REGISTRY.call(name, args))


def test_save_and_sensitive_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_DEFAULT_PATH", tmp_path / "memory.json")
    # store modülü _DEFAULT_PATH'i import anında okumuyor; path() her çağrıda bakar —
    # ama memory_tools varsayılan path kullanır; geçici dizine yönlendirmek için
    # _path fonksiyonunu sar:
    import app.tools.memory_tools as mt
    orig_path = store._path
    monkeypatch.setattr(store, "_path", lambda custom=None: tmp_path / "memory.json")

    r = _call("save_memory", category="tercihler", key="cay", value="şekersiz")
    assert r.ok is True
    data = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert data["tercihler"]["cay"]["value"] == "şekersiz"

    r2 = _call("save_memory", category="x", key="kart", value="4111 1111 1111 1111")
    assert r2.ok is False and r2.error == "sensitive_rejected"
    r3 = _call("save_memory", category="x", key="tckn", value="kimlik 10000000146")
    assert r3.ok is False


def test_delete_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_path", lambda custom=None: tmp_path / "memory.json")
    _call("save_memory", category="notlar", key="sut", value="al")
    r = _call("delete_memory", category="notlar", key="sut")
    assert r.ok is True
    r_empty = _call("delete_memory", category="notlar", key="sut")
    assert r_empty.ok is True and "boş" in r_empty.message
    _call("save_memory", category="notlar", key="ekmek", value="al")
    r_nf = _call("delete_memory", category="notlar", key="yok_boyle_sey")
    assert r_nf.ok is False and r_nf.error == "not_found"


def test_atomic_write_no_tmp_left(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_path", lambda custom=None: tmp_path / "memory.json")
    _call("save_memory", category="a", key="b", value="c")
    leftovers = list(tmp_path.glob("*.tmp-*"))
    assert leftovers == []
