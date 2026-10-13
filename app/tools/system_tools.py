"""Sistem araçları — legacy portu (davranış aynı, arayüz registry).

sys_info: SAFE (salt okuma). open_app: LOW (uygulama açma, loglanır).
Güvenlik notu: open_app bilinmeyen adı 'start' ile dener — PATH dışı keyfi
çalıştırma riski için ad uzunluğu sınırlı, shell yok (doğrudan Popen).
"""
from __future__ import annotations

import datetime
import os
import shutil
import subprocess

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

from app.tools.registry import Risk, ToolResult, tool

APP_ALIASES = {
    "edge": "msedge", "microsoft edge": "msedge",
    "chrome": "chrome", "google chrome": "chrome",
    "firefox": "firefox", "terminal": "cmd", "cmd": "cmd",
    "powershell": "powershell", "explorer": "explorer",
    "dosya gezgini": "explorer", "file explorer": "explorer",
    "spotify": "Spotify", "vscode": "code", "vs code": "code", "code": "code",
    "discord": "Discord", "slack": "Slack", "whatsapp": "WhatsApp",
    "telegram": "Telegram", "zoom": "Zoom", "notepad": "notepad",
    "notlar": "notepad", "not defteri": "notepad", "word": "winword",
    "excel": "excel", "powerpoint": "powerpnt", "calculator": "calc",
    "hesap makinesi": "calc", "task manager": "taskmgr",
    "görev yöneticisi": "taskmgr", "settings": "ms-settings:",
    "ayarlar": "ms-settings:", "paint": "mspaint", "wordpad": "wordpad",
    "snipping tool": "SnippingTool", "ekran alıntısı": "SnippingTool",
    "photos": "ms-photos:", "fotoğraflar": "ms-photos:",
    "maps": "bingmaps:", "haritalar": "bingmaps:",
    "mail": "outlookmail:", "calendar": "outlookcal:", "takvim": "outlookcal:",
    "store": "ms-windows-store:", "mağaza": "ms-windows-store:",
    "music": "mswindowsmusic:", "müzik": "mswindowsmusic:",
    "notion": "Notion",
}

URI_SCHEMES = ("ms-settings:", "ms-photos:", "bingmaps:", "outlookmail:",
               "outlookcal:", "ms-windows-store:", "mswindowsmusic:")


def _battery() -> str:
    if _HAS_PSUTIL:
        try:
            bat = psutil.sensors_battery()
            if bat:
                status = "Şarj oluyor" if bat.power_plugged else "Pilde"
                return f"Pil: %{bat.percent:.0f} — {status}"
        except Exception:
            pass
    return "Pil bilgisi alınamadı (masaüstü bilgisayar olabilir)."


def _sys_info_impl(query: str) -> str:
    query = (query or "").lower().strip()
    results = []
    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "işlemci", "all") and _HAS_PSUTIL:
        try:
            usage = psutil.cpu_percent(interval=0.5)
            count = psutil.cpu_count(logical=True)
            results.append(f"CPU: %{usage:.1f} kullanım — {count} çekirdek")
        except Exception:
            results.append("CPU bilgisi alınamadı.")
    if query in ("ram", "bellek", "memory", "all") and _HAS_PSUTIL:
        try:
            vm = psutil.virtual_memory()
            results.append(f"RAM: {vm.used / 1024**3:.1f}GB / {vm.total / 1024**3:.1f}GB (%{vm.percent:.0f})")
        except Exception:
            results.append("RAM bilgisi alınamadı.")
    if query in ("disk", "depolama", "all") and _HAS_PSUTIL:
        try:
            du = psutil.disk_usage("C:\\")
            results.append(f"Disk (C:): {du.free / 1024**3:.1f}GB boş (toplam {du.total / 1024**3:.1f}GB)")
        except Exception:
            results.append("Disk bilgisi alınamadı.")
    if query in ("time", "saat", "zaman", "all"):
        results.append(f"Saat: {datetime.datetime.now().strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        results.append(f"Tarih: {datetime.datetime.now().strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "wifi", "all"):
        results.append(_network())
    if not results:
        return f"Bilinmeyen sorgu: {query}. battery/cpu/ram/disk/time/date/network/all kullanın."
    return "\n".join(results)


def _network() -> str:
    try:
        out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"],
                                      text=True, timeout=5, stderr=subprocess.DEVNULL,
                                      encoding="utf-8", errors="replace")
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[-1].strip()
                if ssid:
                    return f"WiFi: {ssid} bağlı"
    except Exception:
        pass
    return "Ağ bilgisi alınamadı."


@tool(name="sys_info", description="Sistem bilgisi: pil, CPU, RAM, disk, saat, tarih, ağ.",
      risk=Risk.SAFE,
      params={"query": ("string", "battery | cpu | ram | disk | time | date | network | all", True)})
def sys_info(query: str) -> ToolResult:
    return ToolResult(ok=True, message=_sys_info_impl(query))


@tool(name="app_open", description="Windows'ta uygulama açar (takma ad destekli).",
      risk=Risk.LOW,
      params={"app_name": ("string", "Uygulama adı (örn. Spotify, Not Defteri)", True)})
def app_open(app_name: str) -> ToolResult:
    if not app_name or not app_name.strip():
        return ToolResult(ok=False, message="Uygulama adı belirtilmedi.", error="bad_args")
    if len(app_name) > 80:
        return ToolResult(ok=False, message="Uygulama adı çok uzun.", error="bad_args")
    normalized = app_name.lower().strip()
    resolved = APP_ALIASES.get(normalized, app_name.strip())
    try:
        if resolved.startswith(URI_SCHEMES):
            os.startfile(resolved)
            return ToolResult(ok=True, message=f"{app_name} açıldı.")
        exe_path = shutil.which(resolved)
        if exe_path:
            subprocess.Popen([exe_path], shell=False)
            return ToolResult(ok=True, message=f"{app_name} açıldı.")
        os.startfile(resolved)
        return ToolResult(ok=True, message=f"{app_name} açıldı.")
    except Exception as exc:
        return ToolResult(ok=False, message=f"'{app_name}' açılamadı.",
                          error=f"{type(exc).__name__}: {exc}")
