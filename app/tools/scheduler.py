"""Yerel zamanlayıcı + görevler — Faz 3 (APScheduler + SQLite kalıcılık).

- Hatırlatmalar: zaman gelince Windows toast + sesli uyarı.
- Uygulama kapalıyken kaçırılanlar açılışta bildirilir (kalıcı SQLite).
- APScheduler (kalıcı job store) + ayrı thread.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False

from app.tools.registry import Risk, ToolResult, tool

JOBS_DB = Path(__file__).resolve().parent.parent / "data" / "scheduler.sqlite"
REMINDERS_FILE = Path(__file__).resolve().parent.parent / "data" / "reminders.json"


class SchedulerManager:
    def __init__(self, notify_cb: Optional[Callable[[str], None]] = None):
        self.notify_cb = notify_cb
        self._scheduler: Optional[BackgroundScheduler] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._initialized = False

    def start(self) -> None:
        if self._initialized:
            return
        if not _HAS_APSCHEDULER:
            return
        self._init_db()
        jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{JOBS_DB}")}
        self._scheduler = BackgroundScheduler(jobstores=jobstores, timezone="local")
        self._scheduler.start()
        self._thread = threading.Thread(target=self._check_missed, daemon=True, name="UltronScheduler")
        self._thread.start()
        self._initialized = True

    def _init_db(self) -> None:
        JOBS_DB.parent.mkdir(parents=True, exist_ok=True)

    def shutdown(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def add_reminder(self, text: str, when: datetime, repeat: Optional[str] = None) -> str:
        """Hatırlatıcı ekler. when = datetime (tz-aware). repeat: 'daily', 'weekly', 'monthly'."""
        if not _HAS_APSCHEDULER:
            return "APScheduler yok"
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.now().astimezone().tzinfo)
        job_id = f"remind_{int(time.time() * 1000)}"
        trigger = DateTrigger(run_date=when)
        self._scheduler.add_job(
            self._fire_reminder,
            trigger,
            args=[text],
            id=job_id,
            replace_existing=True,
            misfire_grace_time=300,
        )
        self._persist_reminder(job_id, text, when.isoformat(), repeat)
        return job_id

    def remove_reminder(self, job_id: str) -> bool:
        if not self._scheduler:
            return False
        try:
            self._scheduler.remove_job(job_id)
            self._remove_persisted(job_id)
            return True
        except Exception:
            return False

    def _fire_reminder(self, text: str) -> None:
        if self.notify_cb:
            self.notify_cb(f"⏰ Hatırlatıcı: {text}")
        # Toast notification (Windows)
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            toaster.show_toast("ULTRON Hatırlatıcı", text, duration=10, threaded=True)
        except Exception:
            pass

    def _persist_reminder(self, job_id: str, text: str, when_iso: str, repeat: Optional[str]) -> None:
        reminders = self._load_reminders()
        reminders[job_id] = {"text": text, "when": when_iso, "repeat": repeat, "created": datetime.now().isoformat()}
        self._save_reminders(reminders)

    def _load_reminders(self) -> dict:
        try:
            if REMINDERS_FILE.exists():
                return json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    def _save_reminders(self, reminders: dict) -> None:
        REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = REMINDERS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(reminders, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(REMINDERS_FILE)

    def _remove_persisted(self, job_id: str) -> None:
        reminders = self._load_reminders()
        reminders.pop(job_id, None)
        self._save_reminders(reminders)

    def _check_missed(self) -> None:
        """Uygulama kapalıyken kaçırılan hatırlatıcıları başlatır."""
        while not self._stop.is_set():
            try:
                reminders = self._load_reminders()
                now = datetime.now().astimezone()
                for job_id, r in list(reminders.items()):
                    when = datetime.fromisoformat(r["when"])
                    if when < datetime.now().astimezone():
                        # Kaçırılmış — hemen ateşle
                        self._fire_reminder(f"(Kaçırılan) {r['text']}")
                        if r.get("repeat"):
                            # Tekrar edense yeniden planla
                            next_time = self._next_repeat(when, r["repeat"])
                            self.add_reminder(r["text"], next_time, r["repeat"])
                        else:
                            self.remove_reminder(job_id)
                time.sleep(30)
            except Exception:
                time.sleep(30)

    def _next_repeat(self, base: datetime, repeat: str) -> datetime:
        if repeat == "daily":
            return base + timedelta(days=1)
        if repeat == "weekly":
            return base + timedelta(weeks=1)
        if repeat == "monthly":
            # Basit: 30 gün sonrası
            return base + timedelta(days=30)
        return base + timedelta(days=1)


_SCHEDULER: Optional[SchedulerManager] = None


def get_scheduler(notify_cb: Optional[Callable[[str], None]] = None) -> SchedulerManager:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = SchedulerManager(notify_cb)
        _SCHEDULER.start()
    return _SCHEDULER


# --- Tools ---

@tool(
    name="reminder_add",
    description="Yerel hatırlatıcı ekler. Zaman ISO formatında. repeat: daily/weekly/monthly.",
    risk=Risk.MEDIUM,
    params={
        "text": ("string", "Hatırlatma metni", True),
        "when_iso": ("string", "Zaman (ISO, örn 2026-10-15T14:00:00+03:00)", True),
        "repeat": ("string", "daily/weekly/monthly (opsiyonel)", False),
    })
def reminder_add(text: str, when_iso: str, repeat: str = "") -> ToolResult:
    try:
        when = datetime.fromisoformat(when_iso.replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.now().astimezone().tzinfo)
    except Exception:
        return ToolResult(ok=False, message="Zaman formatı hatalı (ISO gerekli).", error="bad_args")
    sched = get_scheduler()
    job_id = sched.add_reminder(text, when, repeat if repeat else None)
    return ToolResult(ok=True, message=f"Hatırlatıcı eklendi: {job_id} — {text} @ {when_iso}")


@tool(
    name="reminder_list",
    description="Bekleyen hatırlatıcıları listeler.",
    risk=Risk.SAFE,
    params={})
def reminder_list() -> ToolResult:
    # Persisted reminders
    try:
        if REMINDERS_FILE.exists():
            data = json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
            if not data:
                return ToolResult(ok=True, message="Bekleyen hatırlatıcı yok.")
            lines = [f"{k}: {v['text']} @ {v['when']}" for k, v in data.items()]
            return ToolResult(ok=True, message="\n".join(lines))
    except Exception:
        pass
    return ToolResult(ok=True, message="Bekleyen hatırlatıcı yok.")


@tool(
    name="reminder_delete",
    description="Hatırlatıcıyı ID ile siler.",
    risk=Risk.MEDIUM,
    params={"job_id": ("string", "Silinecek hatırlatıcı ID", True)})
def reminder_delete(job_id: str) -> ToolResult:
    sched = get_scheduler()
    if sched.remove_reminder(job_id):
        return ToolResult(ok=True, message=f"Silindi: {job_id}")
    return ToolResult(ok=False, message="Bulunamadı.", error="not_found")