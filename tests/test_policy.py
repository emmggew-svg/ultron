"""Policy Engine testleri — spec §9.1 güvenlik senaryoları."""
from __future__ import annotations

import os
from pathlib import Path

from app.security.policy import (
    DECISION_ALLOW,
    DECISION_CONFIRM,
    DECISION_DENY,
    load_policy,
)


def _pol():
    return load_policy()


# -- kabuk: B-05 regresyonları --
def test_powershell_encoded_denied():
    p = _pol()
    d, _ = p.check_shell("powershell -EncodedCommand aGVsbG8=")
    assert d == DECISION_DENY


def test_cmd_del_denied():
    p = _pol()
    d, _ = p.check_shell("cmd /c del C:\\temp\\x.txt")
    assert d == DECISION_DENY


def test_remove_item_recurse_denied():
    p = _pol()
    d, _ = p.check_shell("Remove-Item -Recurse C:\\Users\\x\\Documents")
    assert d == DECISION_DENY


def test_chained_allowlisted_command_needs_confirm():
    p = _pol()
    d, _ = p.check_shell("dir C:\\Users\\x && echo bitti")
    assert d == DECISION_CONFIRM


def test_pipe_needs_confirm():
    p = _pol()
    d, _ = p.check_shell("tasklist | findstr python")
    assert d == DECISION_CONFIRM


def test_redirect_needs_confirm():
    p = _pol()
    d, _ = p.check_shell("echo merhaba > not.txt")
    assert d == DECISION_CONFIRM


def test_plain_allowlisted_command_confirm_by_default():
    """always_confirm:true → düz allowlist komutu bile confirm ister."""
    p = _pol()
    d, _ = p.check_shell("dir")
    assert d == DECISION_CONFIRM


def test_unknown_command_denied():
    p = _pol()
    d, _ = p.check_shell("format C:")
    assert d == DECISION_DENY


def test_empty_command_denied():
    p = _pol()
    assert p.check_shell("")[0] == DECISION_DENY
    assert p.check_shell("   ")[0] == DECISION_DENY


# -- yollar --
def test_windows_dir_denied():
    p = _pol()
    assert p.check_path("C:\\Windows\\System32\\cmd.exe") == DECISION_DENY


def test_parent_escape_denied():
    home = Path(os.path.expandvars("%USERPROFILE%"))
    evil = str(home / "Documents" / ".." / ".." / "Windows" / "x.dll")
    assert _pol().check_path(evil) == DECISION_DENY


def test_unc_denied():
    assert _pol().check_path("\\\\server\\paylasim\\dosya.txt") == DECISION_DENY


def test_ssh_dir_denied():
    p = _pol()
    assert p.check_path("%USERPROFILE%\\.ssh\\id_rsa") == DECISION_DENY


def test_allowed_root_allowed(tmp_path):
    """Geçici bir allowed_root ile pozitif yol testi."""
    p = _pol()
    p.allowed_roots = [str(tmp_path)]
    p.denied_roots = []
    assert p.check_path(str(tmp_path / "not.txt")) == DECISION_ALLOW


# -- araç kararları --
def test_high_tool_needs_confirm():
    assert _pol().check_tool("HIGH", False) == DECISION_CONFIRM
    assert _pol().check_tool("CRITICAL", False) == DECISION_CONFIRM
    assert _pol().check_tool("LOW", False) == DECISION_ALLOW


def test_policy_yaml_loads():
    """policy.yaml dosyası okunabilmeli ve allowlist'i içermeli."""
    p = load_policy()
    assert "git" in [c.lower() for c in p.shell.allowed_commands]
    assert p.shell.always_confirm is True
    assert p.default_decision == DECISION_DENY
