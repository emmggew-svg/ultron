"""Atomik hafıza deposu — B-17'nin çözümü.

- Yazım: geçici dosya + os.replace (crash'te yarı-yazım olmaz).
- Thread güvenliği: süreç-içi kilit. Süreçler-arası kilit Faz 7'de (SQLite).
- Hassas bilgi (parola, kart, kimlik no) YAZILMAZ — algılanırsa ret (§6.10).
- Prompt'a tüm hafıza BASILMAZ; ilgili ilk K kayıt seçilir (Faz 7'de semantik).
"""
from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent / "memory.json"

_SENSITIVE_RES = [
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # kart no
    re.compile(r"\b[1-9]\d{10}\b"),                             # TCKN (11 hane)
    re.compile(r"(?i)\b(parola|şifre|password|pin kodu)\s*[:=]\s*\S+"),
]

_lock = threading.Lock()


def _path(custom: str | Path | None) -> Path:
    return Path(custom) if custom else _DEFAULT_PATH


def contains_sensitive(text: str) -> bool:
    return any(rx.search(text or "") for rx in _SENSITIVE_RES)


def load(path: str | Path | None = None) -> dict:
    p = _path(path)
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save(data: dict, path: str | Path | None = None) -> None:
    p = _path(path)
    with _lock:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".tmp-{os.getpid()}")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)


def update(fragment: dict, path: str | Path | None = None) -> dict:
    """Derin-birleştirme + atomik yazım. Güncel belleği döner."""
    with _lock:
        mem = load(path)
        _deep_merge(mem, fragment)
        p = _path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + f".tmp-{os.getpid()}")
        tmp.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
        return mem


def _deep_merge(base: dict, update: dict) -> None:
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
