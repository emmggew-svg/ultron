"""Scheduler testleri — yerel hatırlatıcı (mock)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.tools.scheduler import get_scheduler, SchedulerManager


def test_reminder_roundtrip(tmp_path):
    import app.tools.scheduler as sched_mod
    sched = SchedulerManager()
    sched.start()
    try:
        when = (datetime.now(timezone.utc) + timedelta(seconds=2)).isoformat()
        job_id = sched.add_reminder("Test hatırlatma", datetime.now(timezone.utc) + timedelta(seconds=2))
        assert job_id.startswith("remind_")
        time.sleep(3)
        # thread içinde ateşlenmiş olmalı
    finally:
        sched.shutdown()


def test_reminder_persisted(tmp_path):
    import app.tools.scheduler as sched_mod
    import json
    sched = SchedulerManager()
    sched.start()
    try:
        when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        job_id = sched.add_reminder("Yarın toplantı", datetime.now(timezone.utc) + timedelta(days=1))
        # persisted dosyaya yazılmış mı?
        from app.tools.scheduler import REMINDERS_FILE
        data = json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
        assert job_id in data
    finally:
        sched.shutdown()