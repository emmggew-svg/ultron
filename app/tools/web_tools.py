"""Web araçları — legacy portu. B-13 düzeltmesi: 'JARVIS macOS' user-agent'ı
'ULTRON/1.0' oldu; varsayılan konum ULTRON_WEATHER_LOCATION env'inden okunur.

Güvenlik notu: dış içerik (hava durumu, arama sonuçları) untrusted işaretlidir (§5.6).
"""
from __future__ import annotations

import os
import re
import urllib.parse
import webbrowser

import requests

from app.tools.registry import Risk, ToolResult, tool

USER_AGENT = "ULTRON/1.0"
_VIDEO_ID_RE = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')


@tool(name="browser_open", description="Varsayılan tarayıcıda URL açar veya web araması yapar.",
      risk=Risk.LOW,
      params={
          "action": ("string", "open_url | search | play_youtube", True),
          "url": ("string", "open_url için adres", False),
          "query": ("string", "search/play_youtube için sorgu", False),
      })
def browser_open(action: str, url: str = "", query: str = "") -> ToolResult:
    action = (action or "").strip()
    if action == "open_url":
        if not url:
            return ToolResult(ok=False, message="URL belirtilmedi.", error="bad_args")
        target = url if url.startswith(("http://", "https://")) else "https://" + url
        try:
            webbrowser.open(target)
            return ToolResult(ok=True, message=f"Açıldı: {target}")
        except Exception as exc:
            return ToolResult(ok=False, message="Tarayıcı açılamadı.",
                              error=f"{type(exc).__name__}: {exc}")
    if action == "search":
        if not query:
            return ToolResult(ok=False, message="Arama sorgusu belirtilmedi.", error="bad_args")
        target = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        try:
            webbrowser.open(target)
            return ToolResult(ok=True, message=f"'{query}' için arama açıldı.")
        except Exception as exc:
            return ToolResult(ok=False, message="Tarayıcı açılamadı.",
                              error=f"{type(exc).__name__}: {exc}")
    if action in ("play_youtube", "youtube_play", "play_music"):
        if not query:
            return ToolResult(ok=False, message="YouTube sorgusu belirtilmedi.", error="bad_args")
        try:
            video_id = _find_first_youtube_video(query)
        except Exception:
            video_id = None
        if video_id:
            webbrowser.open(f"https://www.youtube.com/watch?v={video_id}&autoplay=1")
            return ToolResult(ok=True, message=f"YouTube'da oynatılıyor: {query}")
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return ToolResult(ok=True, message=f"Arama sonuçları açıldı: {query}")
    return ToolResult(ok=False, message=f"Bilinmeyen eylem: {action}", error="bad_args")


def _find_first_youtube_video(query: str) -> str | None:
    response = requests.get(
        "https://www.youtube.com/results",
        params={"search_query": query},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    seen: set[str] = set()
    for video_id in _VIDEO_ID_RE.findall(response.text):
        if video_id not in seen:
            return video_id
    return None


@tool(name="get_weather", description="Anlık hava durumu özeti verir.",
      risk=Risk.SAFE,
      params={"location": ("string", "Şehir (boşsa ULTRON_WEATHER_LOCATION)", False)})
def get_weather(location: str = "") -> ToolResult:
    target = (location or os.environ.get("ULTRON_WEATHER_LOCATION") or "Istanbul").strip()
    try:
        response = requests.get(
            f"https://wttr.in/{target}",
            params={"format": "j1"},
            timeout=10,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        current = (response.json().get("current_condition") or [{}])[0]
        parts = []
        if current.get("temp_C"):
            parts.append(f"{current['temp_C']} derece")
        desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "")
        if desc:
            parts.append(desc.lower())
        if current.get("humidity"):
            parts.append(f"nem yüzde {current['humidity']}")
        if not parts:
            return ToolResult(ok=False, message="Hava durumu alınamadı.",
                              error="empty", untrusted_content=True)
        return ToolResult(ok=True, message=f"{target} için hava durumu: " + ", ".join(parts) + ".",
                          untrusted_content=True)
    except Exception as exc:
        return ToolResult(ok=False, message="Hava durumu bilgisi şu anda alınamadı.",
                          error=f"{type(exc).__name__}", untrusted_content=True)
