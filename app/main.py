"""ULTRON giriş noktası — Faz 0: yalnızca bootstrap.

`--check`: UI/mikrofon dokunmadan ortam doğrulaması yapar (import yok, hızlı).
Varsayılan: legacy HUD'u ayrı bir köprü üzerinden açar. Bu köprü GEÇİCİDİR;
Faz 1'den itibaren çekirdek `app/` içine taşınacak ve köprü kaldırılacaktır.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
LEGACY_ROOT = APP_ROOT / "legacy" / "jarvis-windows"

EXPECTED_LEGACY_FILES = [
    "main.py",
    "ui.py",
    "app_config.py",
    "wakeup_listener.py",
    "actions/shell.py",
    "actions/calendar.py",
    "actions/reminders.py",
    "actions/whatsapp.py",
    "core/prompt.txt",
    "memory/memory_manager.py",
]


def run_check() -> int:
    errors: list[str] = []
    print(f"[ULTRON] Python {sys.version.split()[0]}")
    if sys.version_info < (3, 12) or sys.version_info >= (3, 13):
        errors.append(f"Python 3.12 gerekli, bulunan: {sys.version.split()[0]}")

    for rel in EXPECTED_LEGACY_FILES:
        if not (LEGACY_ROOT / rel).exists():
            errors.append(f"legacy dosyası eksik: {rel}")

    try:
        import tkinter  # noqa: F401
    except Exception as exc:
        errors.append(f"tkinter kullanılamıyor: {exc}")

    for mod in ("google.genai", "pyaudio", "psutil", "PIL", "requests", "pyperclip", "mss", "pyautogui"):
        try:
            __import__(mod)
        except Exception as exc:
            errors.append(f"bağımlılık eksik: {mod} ({exc})")

    if errors:
        print("[ULTRON] CHECK BAŞARISIZ:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("[ULTRON] CHECK OK — ortam hazır.")
    return 0


def run_legacy_hud() -> int:
    if not LEGACY_ROOT.exists():
        print(f"[ULTRON] legacy kökü yok: {LEGACY_ROOT}")
        return 1
    sys.path.insert(0, str(LEGACY_ROOT))
    # UYARI: legacy main modül seviyesinde PyAudio() açar; mikrofon gerekir.
    import main as legacy_main

    legacy_main.main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ultron", description="ULTRON bootstrap (Faz 0)")
    parser.add_argument("--check", action="store_true", help="ortam doğrulaması yap, UI açma")
    args = parser.parse_args(argv)
    if args.check:
        return run_check()
    return run_legacy_hud()


if __name__ == "__main__":
    raise SystemExit(main())
