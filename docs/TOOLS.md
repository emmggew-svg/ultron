# TOOLS.md — ULTRON araç kataloğu (Faz 1)

Her araç: şema + risk + onay davranışı tek dosyada (`app/tools/`). Şemalar Gemini'ye
otomatik üretilir; `ok` alanı başarı/hata kararı verir (metin taraması YOK).

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `sys_info` | SAFE | yok | pil/CPU/RAM/disk/saat/tarih/ağ |
| `get_weather` | SAFE | yok | wttr.in özeti (çıktı **untrusted**) |
| `app_open` | LOW | yok | takma adlı uygulama açma |
| `browser_open` | LOW | yok | URL açma / arama / YouTube |
| `save_memory` | LOW | yok | hassas bilgi reddedilir, atomik yazım |
| `delete_memory` | LOW | yok | category/key veya metin eşleşmesi |
| `save_whatsapp_contact` | MEDIUM | yok | rehber kaydı (atomik) |
| `get_reminders` | LOW | yok | yerel hatırlatıcı listesi |
| `get_calendar_events` | LOW | yok | takvim sayfası açar (gerçek okuma Faz 3) |
| `add_calendar_event` | MEDIUM | yok | şablon URL (tarih matematiği düzgün) |
| `add_reminder` | MEDIUM | yok | yerel kayıt (otomatik uyarı Faz 3) |
| `shell_run` | HIGH | **her seferinde** | allowlist + parser; onaysız çalışmaz |
| `send_whatsapp_message` | HIGH | **her seferinde** | alıcı doğrulamalı; pencere-doğrulama Faz 6 |

Onay altyapısı: `app/security/confirm.py` (çekirdek) — Tk penceresi Faz 9'da.
Kayıt: her çağrı `AuditLog`'a hash-zincirli yazılır (recorder Faz 2'de bağlanacak).
