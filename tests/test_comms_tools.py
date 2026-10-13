"""WhatsApp araçları testleri — B-06: onaysız gönderim YOK, alıcı doğrulama VAR."""
from __future__ import annotations

import asyncio

import app.tools.comms_tools as cm
from app.tools.registry import REGISTRY


def _call(name, **args):
    return asyncio.run(REGISTRY.call(name, args))


def test_send_requires_confirmation_gate():
    """Registry kapısı: onaylayıcı yokken gövdeye girilmez."""
    r = _call("send_whatsapp_message", message="selam", phone_number="+905551112233",
              send_now=True)
    assert r.ok is False and r.error == "confirmation_required"


def test_send_empty_message_body(monkeypatch):
    """Gövde doğrulaması (kapıyı baypas etmek için doğrudan çağrı)."""
    tooldef = REGISTRY.get("send_whatsapp_message")
    res = asyncio.run(_run_body(tooldef, message="", phone_number="+905551112233"))
    assert res.ok is False


async def _run_body(tooldef, **kwargs):
    fn = tooldef.func
    if hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    import inspect as _inspect
    out = fn(**kwargs)
    if _inspect.isawaitable(out):
        out = await out
    return out


def test_unknown_contact_body():
    tooldef = REGISTRY.get("send_whatsapp_message")
    res = asyncio.run(_run_body(tooldef, message="selam", recipient_name="olmayan_kisi_xyz"))
    assert res.ok is False and res.error == "contact_not_found"


def test_save_and_find_contact(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "CONTACTS_FILE", tmp_path / "contacts.json")
    r = asyncio.run(_run_body(REGISTRY.get("save_whatsapp_contact"),
                              display_name="Test Annesi", phone_number="+905551112233"))
    assert r.ok is True
    found = cm._find_contact("test annesi")
    assert found and found["value"] == "+905551112233"
    bad = asyncio.run(_run_body(REGISTRY.get("save_whatsapp_contact"),
                                display_name="", phone_number="+905551112233"))
    assert bad.ok is False


def test_phone_validation():
    tooldef = REGISTRY.get("send_whatsapp_message")
    res = asyncio.run(_run_body(tooldef, message="selam", phone_number="12"))
    assert res.ok is False and res.error == "bad_args"
