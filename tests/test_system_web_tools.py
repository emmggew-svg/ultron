"""Sistem + web araçları testleri (tarayıcı AÇMADAN — yalnızca doğrulama yolları)."""
from __future__ import annotations

import asyncio

import app.tools.system_tools as sysmod
import app.tools.web_tools as webmod
from app.tools.registry import REGISTRY


def _call(name, **args):
    return asyncio.run(REGISTRY.call(name, args))


def test_sys_info_time():
    r = _call("sys_info", query="time")
    assert r.ok is True and "Saat:" in r.message


def test_sys_info_unknown():
    r = _call("sys_info", query="zart")
    assert r.ok is True and "Bilinmeyen sorgu" in r.message


def test_app_open_validation():
    r = _call("app_open", app_name="")
    assert r.ok is False
    r = _call("app_open", app_name="x" * 81)
    assert r.ok is False
    r = _call("app_open", app_name="kesinlikle_yok_boyle_bir_uygulama_12345")
    assert r.ok is False  # bulunamadı; yan etki yok


def test_browser_validation_paths():
    assert _call("browser_open", action="open_url").ok is False
    assert _call("browser_open", action="search").ok is False
    assert _call("browser_open", action="play_youtube").ok is False
    assert _call("browser_open", action="zart").ok is False


def test_weather_mocked_ok(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"current_condition": [{"temp_C": "12", "FeelsLikeC": "10",
                                           "weatherDesc": [{"value": "Clear"}],
                                           "humidity": "55"}]}

    monkeypatch.setattr(webmod.requests, "get", lambda *a, **k: Resp())
    r = _call("get_weather", location="Ankara")
    assert r.ok is True and "Ankara" in r.message
    assert r.untrusted_content is True  # §5.6: dış içerik işaretli


def test_weather_failure_flagged(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("yok")

    monkeypatch.setattr(webmod.requests, "get", boom)
    r = _call("get_weather", location="Ankara")
    assert r.ok is False and r.untrusted_content is True


def test_no_macos_user_agent_left():
    assert webmod.USER_AGENT == "ULTRON/1.0"
    assert "macOS" not in webmod.USER_AGENT and "JARVIS" not in webmod.USER_AGENT
