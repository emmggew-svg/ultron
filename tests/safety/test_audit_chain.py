"""Audit zincir testleri — spec §5.4: kurcalama tespiti + redaksiyon."""
from __future__ import annotations

import sqlite3

from app.security.audit import AuditLog, redact_args


def test_chain_verifies(tmp_path):
    log = AuditLog(tmp_path / "audit.db")
    log.log(source="test", tool="sys_info", args={"query": "time"},
            risk="SAFE", decision="auto", result_summary="ok", duration_ms=3)
    log.log(source="test", tool="shell_run", args={"command": "dir"},
            risk="HIGH", decision="denied", result_summary="onay yok", duration_ms=1)
    ok, count = log.verify_chain()
    assert ok is True and count == 2


def test_tamper_detected(tmp_path):
    db = tmp_path / "audit.db"
    log = AuditLog(db)
    log.log(source="test", tool="sys_info", args={}, risk="SAFE",
            decision="auto", result_summary="ok")
    with sqlite3.connect(str(db)) as con:
        con.execute("UPDATE audit_log SET result_summary='degistirildi' WHERE id=1")
        con.commit()
    ok, _ = AuditLog(db).verify_chain()
    assert ok is False


def test_secrets_redacted():
    clean = redact_args({"api_key": "sk-abc123", "query": "time",
                         "token": "ya29.xyz", "uzun": "x" * 500})
    assert clean["api_key"] == "***REDACTED***"
    assert clean["token"] == "***REDACTED***"
    assert clean["query"] == "time"
    assert clean["uzun"].endswith("[kısaltıldı]")


def test_recent_lists(tmp_path):
    log = AuditLog(tmp_path / "audit.db")
    log.log(source="ses", tool="app_open", args={"app_name": "Notepad"},
            risk="LOW", decision="auto", result_summary="açıldı")
    rows = log.recent(5)
    assert len(rows) == 1 and rows[0]["tool"] == "app_open"
