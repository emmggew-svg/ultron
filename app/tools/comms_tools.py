"""WhatsApp araçları — legacy portu + B-06 düzeltmeleri.

B-06'nın üç ayağı:
1. Alıcı ad + numara DOĞRULANIR (rehber eşleşmesi + uluslararası format) ✔ burada
2. Gönderim HER ZAMAN ONAYLIDIR (HIGH + requires_confirmation; registry kapısı) ✔ burada
3. Pencere başlığı doğrulaması → Faz 6 (UIA altyapısıyla), bk. DECISIONS D-06.

`send_now=true` yalnızca onaydan SONRA çalışır; onaysız çağrı registry'de reddedilir.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
import urllib.parse
import webbrowser
from pathlib import Path

from app.tools.registry import Risk, ToolResult, tool

try:
    import pyperclip
    _HAS_PYPERCLIP = True
except Exception:
    _HAS_PYPERCLIP = False

try:
    import pyautogui
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

AUTO_SEND_DELAY_SECONDS = 2.4
CONTACTS_FILE = Path(__file__).resolve().parent.parent / "memory" / "contacts.json"


def _normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D+", "", phone_number or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10:
        digits = "90" + digits
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("Telefon numarası uluslararası formatta olmalı. Örn: +905551112233")
    return digits


def _normalize_lookup(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    return re.sub(r"\s+", " ", text)


def _load_contacts() -> dict:
    try:
        if CONTACTS_FILE.exists():
            data = json.loads(CONTACTS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_contacts(contacts: dict) -> None:
    CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONTACTS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONTACTS_FILE)  # atomik yazım (B-17)


def _find_contact(name: str) -> dict | None:
    needle = _normalize_lookup(name)
    if not needle:
        return None
    best, best_score = None, 0
    for key, entry in _load_contacts().items():
        if not isinstance(entry, dict):
            continue
        names = [str(entry.get("display_name", "")), str(key)]
        aliases = entry.get("aliases", [])
        names.extend(str(a) for a in aliases) if isinstance(aliases, list) else names.append(str(aliases))
        for cand in names:
            cn = _normalize_lookup(cand)
            score = 300 if cn == needle else (220 if cn.startswith(needle) or needle.startswith(cn) else (160 if needle in cn else 0))
            if score > best_score:
                best, best_score = dict(entry, display_name=entry.get("display_name", key)), score
    return best


@tool(name="save_whatsapp_contact",
      description="WhatsApp kişisini numarasıyla kaydeder (ad + uluslararası format zorunlu).",
      risk=Risk.MEDIUM,
      params={
          "display_name": ("string", "Kişi adı", True),
          "phone_number": ("string", "Telefon (+9055...)", True),
          "aliases": ("string", "Virgüllü takma adlar", False),
      })
def save_whatsapp_contact(display_name: str, phone_number: str, aliases: str = "") -> ToolResult:
    if not (display_name or "").strip():
        return ToolResult(ok=False, message="Kişi adı boş olamaz.", error="bad_args")
    try:
        normalized = _normalize_phone(phone_number)
    except ValueError as exc:
        return ToolResult(ok=False, message=str(exc), error="bad_args")
    alias_list = [p.strip() for p in (aliases or "").split(",") if p.strip()]
    key = re.sub(r"[^a-z0-9]+", "_", _normalize_lookup(display_name)).strip("_") or "contact"
    contacts = _load_contacts()
    contacts[key] = {"value": f"+{normalized}", "display_name": display_name.strip(),
                     "aliases": alias_list}
    try:
        _save_contacts(contacts)
    except Exception as exc:
        return ToolResult(ok=False, message="Rehber yazılamadı.", error=str(exc))
    return ToolResult(ok=True, message=f"{display_name.strip()} kaydedildi.")


def _auto_send() -> tuple[bool, str]:
    if not _HAS_PYAUTOGUI:
        return False, "pyautogui kurulu değil"
    try:
        time.sleep(AUTO_SEND_DELAY_SECONDS)
        pyautogui.press("enter")
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


@tool(name="send_whatsapp_message",
      description="WhatsApp'tan mesaj hazırlar/gönderir. GÖNDERİM HER ZAMAN ONAYLIDIR (HIGH).",
      risk=Risk.HIGH,
      requires_confirmation=True,
      params={
          "message": ("string", "Mesaj metni", True),
          "phone_number": ("string", "Doğrudan numara (rehber yerine)", False),
          "recipient_name": ("string", "Rehberdeki kişi adı", False),
          "send_now": ("boolean", "true ise Enter'a basıp gönderir (onay sonrası)", False),
      },
      timeout=60.0)
def send_whatsapp_message(message: str, phone_number: str = "",
                          recipient_name: str = "", send_now: bool = False) -> ToolResult:
    # NOT: bu gövdeye yalnızca onaydan SONRA girilir (registry kapısı).
    if not (message or "").strip():
        return ToolResult(ok=False, message="Mesaj boş olamaz.", error="bad_args")
    normalized = ""
    if (phone_number or "").strip():
        try:
            normalized = _normalize_phone(phone_number)
        except ValueError as exc:
            return ToolResult(ok=False, message=str(exc), error="bad_args")
    resolved_name = (recipient_name or "").strip()
    if resolved_name and not normalized:
        contact = _find_contact(resolved_name)
        if contact is None:
            return ToolResult(ok=False,
                              message=f"'{resolved_name}' rehberde bulunamadı. Önce numarasıyla kaydedin.",
                              error="contact_not_found")
        try:
            normalized = _normalize_phone(str(contact.get("value", "")))
        except ValueError:
            return ToolResult(ok=False, message="Kayıtlı numara geçersiz.", error="bad_args")
        resolved_name = str(contact.get("display_name", resolved_name))
    if not normalized:
        return ToolResult(ok=False, message="Kişi adı veya telefon numarası gerekli.", error="bad_args")

    url = f"https://web.whatsapp.com/send?phone={normalized}&text={urllib.parse.quote(message.strip())}"
    try:
        webbrowser.open(url)
    except Exception as exc:
        return ToolResult(ok=False, message="WhatsApp açılamadı.", error=str(exc))
    label = resolved_name or f"+{normalized}"
    if not send_now:
        return ToolResult(ok=True, message=f"{label} için WhatsApp sohbeti açıldı (taslak, gönderilmedi).",
                          data={"phone": f"+{normalized}"})
    # Faz 6'ya kadar: pencere başlığı doğrulaması YOK — kullanıcı onayı tek güvence (bk. D-06).
    ok_send, detail = _auto_send()
    if ok_send:
        return ToolResult(ok=True, message=f"{label} kişisine mesaj gönderildi.",
                          data={"phone": f"+{normalized}"})
    return ToolResult(ok=False, message=f"Sohbet açıldı ama otomatik gönderim yapılamadı: {detail}.",
                      error="auto_send_failed")
