"""Takvim/görev testleri (tarayıcı açan yollar çağrılmaz; ayrıştırma + depo test edilir)."""
from __future__ import annotations

import asyncio
import datetime

import app.tools.task_tools as tt
from app.tools.registry import REGISTRY

import app.tools.memory_tools  # noqa: F401


def _call(name, **args):
    return asyncio.run(REGISTRY.call(name, args))


def test_date_math_end_defaults_plus_one_hour():
    tooldef = REGISTRY.get("add_calendar_event")
    # gövdeyi doğrudan çağırıp şablon URL'sini yakala
    opened = []
    import webbrowser
    orig = webbrowser.open
    webbrowser.open = lambda url: opened.append(url) or True
    try:
        res = asyncio.run(_run_body(tooldef, title="Disci",
                                    start_iso="2026-10-14T14:00:00"))
    finally:
        webbrowser.open = orig
    assert res.ok is True
    assert "20261014T140000/20261014T150000" in res.data["dates"], res.data


def test_end_before_start_rejected():
    tooldef = REGISTRY.get("add_calendar_event")
    res = asyncio.run(_run_body(tooldef, title="X",
                                start_iso="2026-10-14T14:00:00",
                                end_iso="2026-10-14T13:00:00"))
    assert res.ok is False and res.error == "bad_args"


def test_all_day_span():
    tooldef = REGISTRY.get("add_calendar_event")
    import webbrowser
    orig = webbrowser.open
    webbrowser.open = lambda url: True
    try:
        res = asyncio.run(_run_body(tooldef, title="Tatil",
                                    start_iso="2026-10-14", all_day=True))
    finally:
        webbrowser.open = orig
    assert res.ok is True and res.data["dates"] == "20261014/20261015"


async def _run_body(tooldef, **kwargs):
    import inspect as _inspect
    out = tooldef.func(**kwargs)
    if _inspect.isawaitable(out):
        out = await out
    return out


def test_reminder_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(tt, "TASKS_FILE", tmp_path / "tasks.json")
    r = _call("add_reminder", title="Süt al", due_iso="2026-10-14T18:00:00")
    assert r.ok is True and "Faz 3" in r.message  # uyarı yokluğu açıkça yazılır
    r2 = _call("get_reminders")
    assert r2.ok is True and "Süt al" in r2.message
    r3 = _call("add_reminder", title="X", due_iso="anlaşılmaz")
    assert r3.ok is False
