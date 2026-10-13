"""Faz 2 duman testi — gerçek Live bağlantısı (API anahtarı + mikrofon gerekir).

Kullanım (KULLANICININ kendi terminalinde — anahtar kimseyle paylaşılmaz):
    $env:GEMINI_API_KEY = "AIza..."
    .\\.venv\\Scripts\\python.exe scripts\\live_smoke.py --dakika 5

Ne yapar:
- Charon sesiyle gemini-3.8-live'a bağlanır, mikrofonu açar, hoparlörden çalar.
- Konuş: "saat kaç?" (sys_info aracı gerçekten çalışır).
- Araya gir: Ultron konuşurken konuş → susmalı (barge-in).
- Çıkış: Ctrl+C veya süre dolumu. Olaylar konsola yazılır.
KULAKLIK ÖNERİLİR (hoparlör yankısı mikrofona girer).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.events import BUS
from app.tools.loader import load_all
from app.voice.audio_io import AudioIO
from app.voice.live_session import LiveSessionManager


def build_system_text() -> str:
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "app", "core", "prompts", "system.md")
    with open(prompt_path, encoding="utf-8") as f:
        prompt = f.read()
    now = datetime.datetime.now().strftime("%A, %d %B %Y — %H:%M")
    return f"[ŞU ANKİ ZAMAN]\n{now}\n\n{prompt}\n\nNOT: Bu bir bağlantı testidir. Kısa cevap ver."


def on_event(event: str, payload) -> None:
    if event == "state_changed":
        print(f"[DURUM] {payload}")
    elif event == "user_utterance":
        print(f"[SEN] {payload.get('text', '')}")
    elif event == "assistant_utterance":
        print(f"[ULTRON] {payload.get('text', '')}")
    elif event == "tool_requested":
        print(f"[ARAÇ] çağrıldı: {payload.get('tools')}")
    elif event == "tool_completed":
        print(f"[ARAÇ] bitti: ok={payload.get('ok')} — {payload.get('message', '')[:120]}")
    elif event == "assistant_interrupted":
        print(f"[BARGE-IN] sustu, atılan parça: {payload.get('dropped_chunks')}")
    elif event == "error":
        print(f"[HATA] {payload}")


async def amain(minutes: float) -> int:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("HATA: GEMINI_API_KEY boş. Önce kendi terminalinde tanımla:")
        print('  $env:GEMINI_API_KEY = "AIza..."')
        return 2

    from google import genai

    load_all()
    for name in ("state_changed", "user_utterance", "assistant_utterance",
                 "tool_requested", "tool_completed", "assistant_interrupted", "error"):
        BUS.on(name, on_event)

    audio = AudioIO(hardware=True)
    try:
        audio.start_input()
    except Exception as exc:
        print(f"HATA: mikrofon açılamadı: {exc}")
        return 3

    manager = LiveSessionManager(system_text=build_system_text(), audio=audio)
    play_task = asyncio.create_task(audio.play_loop())
    stopper = asyncio.create_task(_stop_after(manager, minutes * 60))
    print(f"[ULTRON] Bağlanıyor... (model: gemini-3.8-live, ses: Charon, süre: {minutes} dk)")
    print("[ULTRON] Konuşabilirsin. Çıkış: Ctrl+C.")
    try:
        await manager.run_forever(lambda: genai.Client(api_key=api_key))
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[ULTRON] Kapatılıyor...")
    finally:
        manager.stop()
        stopper.cancel()
        play_task.cancel()
        audio.stop_input()
    print("[ULTRON] Bitti. Gözlemlerini RUNBOOK Faz 2 listesine işle.")
    return 0


async def _stop_after(manager: LiveSessionManager, seconds: float) -> None:
    await asyncio.sleep(seconds)
    print(f"\n[ULTRON] Süre doldu ({seconds / 60:.0f} dk). Durduruluyor...")
    manager.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="ULTRON Faz 2 duman testi")
    parser.add_argument("--dakika", type=float, default=5.0)
    args = parser.parse_args()
    return asyncio.run(amain(args.dakika))


if __name__ == "__main__":
    raise SystemExit(main())
