"""shell_run testleri — B-05 regresyonu: allowlist esastır, onaysız çalışmaz."""
from __future__ import annotations

import asyncio

import app.tools.shell_tool as st
from app.tools.registry import REGISTRY


def _call(**args):
    return asyncio.run(REGISTRY.call("shell_run", args))


def test_encoded_denied():
    # HIGH kapısı önce devreye girer (confirmation_required) veya policy reddeder —
    # ikisi de "çalışmadı" demektir. Policy katmanı test_policy.py'de doğrudan test edilir.
    r = _call(command="powershell -EncodedCommand xyz")
    assert r.ok is False
    assert r.error == "confirmation_required" or r.error.startswith("policy_deny")


def test_unknown_command_denied():
    r = _call(command="format C:")
    assert r.ok is False


def test_chained_needs_confirmation():
    r = _call(command="dir && echo x")
    assert r.ok is False and r.error == "confirmation_required"


def test_plain_command_needs_confirmation():
    r = _call(command="dir")
    assert r.ok is False and r.error == "confirmation_required"


def test_redaction():
    masked = st._redact("key sk-abc123XYZ789 deneme nvapi-AAAAbbbbCCCC1234 son")
    assert "sk-abc123XYZ789" not in masked and "nvapi-AAAAbbbbCCCC1234" not in masked
    assert "***REDACTED***" in masked


def test_allow_path_runs(monkeypatch):
    """Policy allow verirse komut gerçekten çalışır (izole kök, zararsız komut)."""

    class OpenPolicy:
        shell = type("S", (), {"timeout_seconds": 10, "max_output_chars": 4000})()

        def check_shell(self, cmd):
            return ("allow", "test")

    monkeypatch.setattr(st, "_POLICY", OpenPolicy())
    res = st._run_shell("whoami", 10)
    assert res.ok is True and res.message.strip() != ""


def test_allow_path_exit_code(monkeypatch):
    class OpenPolicy:
        shell = type("S", (), {"timeout_seconds": 10, "max_output_chars": 4000})()

        def check_shell(self, cmd):
            return ("allow", "test")

    monkeypatch.setattr(st, "_POLICY", OpenPolicy())
    res = st._run_shell("where kesinlikle_yok_boyle_bir_sey_12345", 10)
    assert res.ok is False and res.error == "exit:1"
