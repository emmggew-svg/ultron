"""Denetim günlüğü — spec §5.4. SQLite + hash zinciri (kurcalama tespiti).

Kayıt: zaman, kaynak, araç, redakte edilmiş argümanlar, risk, karar, sonuç özeti,
süre, prev_hash + sha256 hash. UI'da "Ne yaptın?" paneli buradan beslenir (Faz 9).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    source TEXT NOT NULL,
    tool TEXT NOT NULL,
    args_redacted TEXT NOT NULL,
    risk TEXT NOT NULL,
    decision TEXT NOT NULL,
    result_summary TEXT NOT NULL,
    duration_ms INTEGER NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);
"""

# Loga düşerken maskelenecek anahtar kalıpları (§5.7)
_SECRET_KEYS = ("key", "token", "secret", "password", "passwd", "auth", "credential")


def redact_args(args: dict) -> dict:
    clean: dict = {}
    for k, v in (args or {}).items():
        kl = str(k).lower()
        if any(s in kl for s in _SECRET_KEYS):
            clean[k] = "***REDACTED***"
        elif isinstance(v, str) and len(v) > 200:
            clean[k] = v[:200] + "…[kısaltıldı]"
        else:
            clean[k] = v
    return clean


def _entry_hash(prev_hash: str, payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}|{payload}".encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL;")
        return con

    def log(self, *, source: str, tool: str, args: dict | None = None,
            risk: str = "LOW", decision: str = "auto",
            result_summary: str = "", duration_ms: int = 0) -> int:
        args_json = json.dumps(redact_args(args or {}), ensure_ascii=False, sort_keys=True)
        ts = time.time()
        with self._connect() as con:
            row = con.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
            prev = row[0] if row else "GENESIS"
            payload = f"{ts}|{source}|{tool}|{args_json}|{risk}|{decision}|{result_summary}|{duration_ms}"
            digest = _entry_hash(prev, payload)
            cur = con.execute(
                "INSERT INTO audit_log (ts, source, tool, args_redacted, risk, decision,"
                " result_summary, duration_ms, prev_hash, hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (ts, source, tool, args_json, risk, decision, result_summary,
                 duration_ms, prev, digest),
            )
            con.commit()
            return int(cur.lastrowid)

    def verify_chain(self) -> tuple[bool, int]:
        """Zincir doğrulaması → (sağlam_mı, kayıt_sayısı)."""
        with self._connect() as con:
            rows = con.execute(
                "SELECT ts, source, tool, args_redacted, risk, decision,"
                " result_summary, duration_ms, prev_hash, hash"
                " FROM audit_log ORDER BY id").fetchall()
        prev = "GENESIS"
        for r in rows:
            ts, source, tool, args_json, risk, decision, summary, dur, prev_hash, digest = r
            if prev_hash != prev:
                return False, len(rows)
            payload = f"{ts}|{source}|{tool}|{args_json}|{risk}|{decision}|{summary}|{dur}"
            if _entry_hash(prev, payload) != digest:
                return False, len(rows)
            prev = digest
        return True, len(rows)

    def recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT ts, source, tool, risk, decision, result_summary, duration_ms"
                " FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            {"ts": r[0], "source": r[1], "tool": r[2], "risk": r[3],
             "decision": r[4], "summary": r[5], "duration_ms": r[6]} for r in rows
        ]
