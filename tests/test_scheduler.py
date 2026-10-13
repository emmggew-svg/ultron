"""Scheduler testleri — yerel hatırlatıcı (mock)."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from app.tools.scheduler import SchedulerManager, REMINDERS_FILE


def test_reminder_roundtrip():
    sched = SchedulerManager()
    sched.start()
    try:
        when = datetime.now(timezone.utc) + timedelta(seconds=2)
        job_id = sched.add_reminder("Test hatırlatma", when)
        assert job_id.startswith("remind_")
        time.sleep(3)
        # thread içinde ateşlenmiş olmalı
    finally:
        sched.shutdown()


def test_reminder_persisted(tmp_path):
    import json
    from pathlib import Path
    import app.tools.scheduler as sched_mod

    # Use a temp reminders file
    test_file = tmp_path / "test_reminders.json"
    original_file = sched_mod.REMINDERS_FILE
    sched_mod.REMINDERS_FILE = test_file

    try:
        sched = SchedulerManager()
        sched.start()
        try:
            when = datetime.now(timezone.utc) + timedelta(days=1)
            job_id = sched.add_reminder("Yarın toplantı", when)
            # persisted dosyaya yazılmış mı?
            assert test_file.exists()
            data = json.loads(test_file.read_text(encoding="utf-8"))
            assert job_id in data
        finally:
            sched.shutdown()
    finally:
        sched_mod.REMINDERS_FILE = original_file