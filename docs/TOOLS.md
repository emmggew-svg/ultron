# TOOLS.md — ULTRON araç kataloğu (Faz 3 itibarıyla: 15 araç)

Her araç: şema + risk + onay davranışı tek dosyada (`app/tools/`). Şemalar Gemini'ye
otomatik üretilir; `ok` alanı başarı/hata kararı verir (metin taraması YOK).

## Sistem (system_tools.py)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `sys_info` | SAFE | auto | pil/CPU/RAM/disk/saat/tarih/ağ |
| `app_open` | LOW | auto | takma adlı uygulama açma |

## Web (web_tools.py)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `browser_open` | LOW | auto | URL açma / arama / YouTube (open_url/search/play_youtube) |
| `get_weather` | SAFE | auto | wttr.in özeti (çıktı **untrusted** işaretli) |

## Kabuk (shell_tool.py)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `shell_run` | HIGH | **CONFIRM** | allowlist + parser; onaysız ÇALIŞMAZ |

## İletişim (comms_tools.py)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `save_whatsapp_contact` | MEDIUM | auto | rehber kaydı (atomik yazım) |
| `send_whatsapp_message` | HIGH | **CONFIRM** | alıcı doğrulamalı; pencere-doğrulama Faz 6 |

## Hafıza (memory_tools.py)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `save_memory` | LOW | auto | hassas bilgi reddedilir, atomik yazım |
| `delete_memory` | LOW | auto | category/key veya metin eşleşmesi |

## Google Calendar (google_calendar.py — Faz 3)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `calendar_list` | SAFE | auto | etkinlikleri aralıktır, listeler |
| `calendar_create` | MEDIUM | auto | ISO başlangıç/bitiş ile etkinlik oluştur |
| `calendar_delete` | HIGH | **CONFIRM** | event_id ile sil |

## Zamanlayıcı (scheduler.py — Faz 3)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `reminder_add` | MEDIUM | auto | APScheduler + SQLite kalıcı hatırlatıcı |
| `reminder_list` | SAFE | auto | bekleyen hatırlatıcılar |
| `reminder_delete` | MEDIUM | auto | job_id ile sil |

## FAZ 3 REFACTOR NOTU
Faz 1'deki `task_tools.py` placeholder'ları (`add_calendar_event`,
`get_calendar_events`, `add_reminder`, `get_reminders`) silindi — yerine
yukarıdaki **gerçek** Google Calendar + APScheduler araçları geldi.
Toplam araç sayısı: 19 → **15**.

Onay altyapısı: `app/security/confirm.py` (çekirdek) — Tk penceresi Faz 9'da.
Kayıt: her çağrı `AuditLog`'a hash-zincirli yazılır.
