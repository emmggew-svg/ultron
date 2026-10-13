"""Takvim + hatırlatıcı araçları — Faz 1 geçici gerçeklik (B-01/02/03 notu).

- Takvim: Google Calendar şablon URL'si açılır (legacy davranış), ANCAK tarih
  matematiği düzeltildi: end_iso yoksa başlangıç+1s, all_day iki tarih üretir,
  saat dilimi eklenir (B-03). Gerçek Calendar API Faz 3'tedir.
- Hatırlatıcılar: yerel JSON deposu (app/memory/tasks.json) — listele/ekle/sil
  GERÇEKTEN çalışır; zamanı gelince UYARMA Faz 3 zamanlayıcısınındır (B-02).
  Bu yüzden add_reminder sonucu "uyarı Faz 3'te" diye açıkça yazar (uydurma yok).
"""
from __future__ import annotations

import datetime
import json
import urllib.parse
import webbrowser
from pathlib import Path

from app.tools.registry import Risk, ToolResult, tool

TASKS_FILE = Path(__file__).resolve().parent.parent / "memory" / "tasks.json"


def _parse_dt(value: str) -> datetime.datetime | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _fmt_gcal(dt: datetime.datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")


@tool(name="get_calendar_events",
      description="Takvim sayfasını açar (Faz 1: okuma yok — gerçek API Faz 3'te).",
      risk=Risk.LOW,
      params={"query": ("string", "today | tomorrow | next | agenda", False)})
def get_calendar_events(query: str = "today") -> ToolResult:
    try:
        webbrowser.open("https://calendar.google.com")
    except Exception as exc:
        return ToolResult(ok=False, message="Takvim açılamadı.", error=str(exc))
    return ToolResult(ok=True,
                      message="Google Calendar açıldı. (Faz 1 notu: gerçek okuma Faz 3'te gelecek.)")


@tool(name="add_calendar_event",
      description="Google Calendar şablonuyla etkinlik oluşturma sayfası açar.",
      risk=Risk.MEDIUM,
      params={
          "title": ("string", "Başlık", True),
          "start_iso": ("string", "Başlangıç (ISO)", True),
          "end_iso": ("string", "Bitiş (ISO, boşsa +1 saat)", False),
          "notes": ("string", "Notlar", False),
          "location": ("string", "Konum", False),
          "all_day": ("boolean", "Tüm gün", False),
      })
def add_calendar_event(title: str, start_iso: str, end_iso: str = "",
                       notes: str = "", location: str = "", all_day: bool = False) -> ToolResult:
    if not (title or "").strip():
        return ToolResult(ok=False, message="Başlık gerekli.", error="bad_args")
    start = _parse_dt(start_iso)
    if start is None:
        return ToolResult(ok=False, message="Başlangıç tarihi anlaşılmadı (ISO).",
                          error="bad_args")
    if all_day:
        end = start + datetime.timedelta(days=1)
        dates = f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
    else:
        end = _parse_dt(end_iso) if end_iso else None
        if end is None:
            end = start + datetime.timedelta(hours=1)
        if end <= start:
            return ToolResult(ok=False, message="Bitiş başlangıçtan sonra olmalı.",
                              error="bad_args")
        dates = f"{_fmt_gcal(start)}/{_fmt_gcal(end)}"
    params = {"action": "TEMPLATE", "text": title.strip(), "dates": dates}
    if location:
        params["location"] = location
    if notes:
        params["details"] = notes
    url = "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)
    try:
        webbrowser.open(url)
    except Exception as exc:
        return ToolResult(ok=False, message="Tarayıcı açılamadı.", error=str(exc))
    return ToolResult(ok=True,
                      message=f"'{title}' için takvim şablonu açıldı ({dates}).",
                      data={"dates": dates})


def _load_tasks() -> list:
    try:
        if TASKS_FILE.exists():
            data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_tasks(tasks: list) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = TASKS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(TASKS_FILE)


@tool(name="add_reminder",
      description="Yerel hatırlatıcı kaydeder. NOT: otomatik uyarı Faz 3'te gelecek.",
      risk=Risk.MEDIUM,
      params={
          "title": ("string", "Hatırlatma metni", True),
          "due_iso": ("string", "Zaman (ISO, opsiyonel)", False),
          "notes": ("string", "Notlar", False),
      })
def add_reminder(title: str, due_iso: str = "", notes: str = "") -> ToolResult:
    if not (title or "").strip():
        return ToolResult(ok=False, message="Metin gerekli.", error="bad_args")
    due = _parse_dt(due_iso) if due_iso else None
    if due_iso and due is None:
        return ToolResult(ok=False, message="Zaman anlaşılmadı (ISO).", error="bad_args")
    tasks = _load_tasks()
    tasks.append({"title": title.strip(), "due": due.isoformat() if due else "",
                  "notes": notes, "done": False})
    try:
        _save_tasks(tasks)
    except Exception as exc:
        return ToolResult(ok=False, message="Kaydedilemedi.", error=str(exc))
    suffix = " (Not: otomatik uyarı Faz 3 zamanlayıcısıyla gelecek.)" if due else ""
    return ToolResult(ok=True, message=f"Hatırlatıcı kaydedildi: {title.strip()}{suffix}")


@tool(name="get_reminders",
      description="Kaydedilmiş yerel hatırlatıcıları listeler.",
      risk=Risk.LOW,
      params={"query": ("string", "upcoming | all", False)})
def get_reminders(query: str = "upcoming") -> ToolResult:
    tasks = [t for t in _load_tasks() if not t.get("done")]
    if not tasks:
        return ToolResult(ok=True, message="Bekleyen hatırlatıcı yok.")
    lines = [f"- {t.get('title','')}" + (f" ({t['due']})" if t.get("due") else "")
             for t in tasks]
    return ToolResult(ok=True, message="\n".join(lines), data={"count": len(tasks)})
