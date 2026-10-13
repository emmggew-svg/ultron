"""Faz 0 akıl sağlığı testleri: iskelet + legacy referans bütünlüğü."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "legacy" / "jarvis-windows"


def test_python_version_is_312():
    assert sys.version_info[:2] == (3, 12), f"3.12 gerekli: {sys.version}"


def test_legacy_tree_intact():
    for rel in (
        "main.py", "ui.py", "app_config.py", "wakeup_listener.py",
        "actions/shell.py", "actions/calendar.py", "actions/reminders.py",
        "actions/whatsapp.py", "actions/weather.py", "actions/sys_info.py",
        "core/prompt.txt", "memory/memory_manager.py", "requirements.txt",
    ):
        assert (LEGACY / rel).exists(), f"legacy eksik: {rel}"


def test_legacy_shell_still_blocklist_based():
    """B-05'in Faz 0'daki hali: kara liste mevcut (Faz 1'de allowlist'e dönecek)."""
    text = (LEGACY / "actions" / "shell.py").read_text(encoding="utf-8")
    assert "BLOCKED" in text and "shell=True" in text


def test_pyproject_requires_pyautogui():
    """B-10 düzeltmesi: yeni projede pyautogui bağımlılığı şart."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "pyautogui" in text
    assert 'requires-python = "==3.12.*"' in text


def test_app_bootstrap_check_mode():
    sys.path.insert(0, str(ROOT))
    from app.main import EXPECTED_LEGACY_FILES

    for rel in EXPECTED_LEGACY_FILES:
        assert (LEGACY / rel).exists(), rel
