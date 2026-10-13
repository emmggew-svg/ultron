# DECISIONS.md — ULTRON karar ve doğrulama günlüğü

> Spec kuralı §0.8: belirsizlikte varsayım yapma, buraya soru olarak yaz ve en güvenli seçenekle devam et.

## D-01 — Baz kod tabanı seçimi (2026-10-13, Faz 0)
**Karar:** Baz = `legacy/jarvis-windows/` (küçük zip'ten: `main.py` 40.572 B, `ui.py` 89.572 B).
V2'den `tool_defs.py` + `webcam_vision.py` Faz 0/1'de porta dahil. Geri kalan her şey özgün yazılacak.
**Gerekçe:** Spec §2'deki dosya haritası ve 13 araç listesi bu pakete birebir uyuyor.

## D-02 — B-01…B-20 doğrulama sonuçları (2026-10-13, Faz 0)
Kaynak: `legacy/jarvis-windows/`. Tamamı okunarak doğrulandı.

| ID | Sonuç | Kanıt |
|----|-------|-------|
| B-01 | DOĞRULANDI | `actions/calendar.py:17-23` — `get_calendar_events` sadece `webbrowser.open()` yapıyor, veri okumuyor |
| B-02 | DOĞRULANDI | `actions/reminders.py:13-18,21-33` — iki fonksiyonda da sadece To-Do sayfası açılıyor, kayıt/zamanlayıcı yok |
| B-03 | DOĞRULANDI | `actions/calendar.py:39-44` — `end_iso` ve `all_day` parametreleri hiç kullanılmıyor; bitiş=başlangıç; saat dilimi yok; `split("T")[1]` `T` yoksa IndexError riski |
| B-04 | DOĞRULANDI + EK BULGU | `core/prompt.txt:1` "macOS'ta çalışan"; satır 23-28 Apple Calendar/Reminders; satır 69 `ls ~/Desktop`; **ek:** satır 10 "gönder" deyince *ekstra onay isteme, send_now=true kullan* diyor — B-06'yı prompt düzeyinde teşvik ediyor |
| B-05 | DOĞRULANDI | `actions/shell.py:8-30` — 10 maddelik kara liste + `shell=True` (satır 35); `powershell -enc`, `&&` zincirleme, `Remove-Item` varyasyonları listede yok; onay akışı yok |
| B-06 | DOĞRULANDI | `actions/whatsapp.py:200-208` — hedef pencere doğrulaması yok, kör `pyautogui.press("enter")`; `send_now` onaysız tetiklenebilir |
| B-07 | DOĞRULANDI | `main.py:628-653` `_build_config` içinde `session_resumption`/`context_window_compression` yok; kopunca 3 sn bekleyip sıfırdan bağlanıyor |
| B-08 | DOĞRULANDI | `main.py:874-875` mikrofon `not jarvis_speaking` iken kapalı; `_interrupt_audio` (satır 537) tanımlı ama **hiçbir yerden çağrılmıyor**; `interrupted` olayı işlenmiyor |
| B-09 | DOĞRULANDI | `main.py:945-952` — araç `await self._execute_tool(fc)` ile `_receive_audio` döngüsü içinde bekleniyor; `run_in_executor` loop'u kurtarır ama receive işleme yine durur |
| B-10 | DOĞRULANDI | `requirements.txt` 9 satır, `pyautogui` yok; `whatsapp.py:24-28` ImportError'ı sessizce yutuyor |
| B-11 | DOĞRULANDI | `.vscode/launch.json:9` — `C:\Users\Tuna\...` gömülü yol |
| B-12 | DOĞRULANDI | `main.py` import listesinde (satır 8-34) `tts`/`health` yok; `actions/tts.py`, `actions/health.py` ölü kod |
| B-13 | DOĞRULANDI + EK BULGU | `actions/weather.py:18` varsayılan `"Istanbul"`; **ek:** satır 23 `User-Agent: "JARVIS macOS"` — Windows sürümünde macOS izi |
| B-14 | KISMEN (dump doğrulandı, İngilizce-zorlama bulunamadı) | `memory_manager.py:136-156` tüm hafıza prompt'a basılıyor, limit yok; "İngilizce yaz" talimatı kodda/prompt'ta **bulunamadı** |
| B-15 | DOĞRULANDI | `main.py:567-590` `_result_looks_like_error` — "gerekli." gibi genel kelimeler bile hata sayılıyor |
| B-16 | DOĞRULANDI | `app_config.py:10,39-43` — `config/api_keys.json` düz metin yazılıyor; redaksiyon yok |
| B-17 | DOĞRULANDI | `memory_manager.py:31-34` — direkt `open(...,"w")` yazım; kilit yok, crash'te bozulma riski |
| B-18 | DOĞRULANDI | `main.py:52` + `wakeup_listener.py:42` — iki ayrı `PyAudio()` örneği |
| B-19 | DOĞRULANDI | `main.py:55` `TOOL_DECLARATIONS` + satır 666-821 `elif` zinciri; V2'de ek olarak ayrı `tool_defs.py` (üçüncü kopya!) |
| B-20 | DOĞRULANDI | `ui.py` 89.572 byte tek dosya |

## D-03 — V2 vs baz farkları (2026-10-13, Faz 0)
- `tool_defs.py` (17 KB): şemaların ayrı dosyaya çıkarılmış hali — Registry tasarımında referans alınacak, ancak **Türkçe karakterler bozuk** (cp1254 mojibake). Portta baz paketteki doğru metinler kullanılacak.
- `webcam_vision.py` (7.5 KB): bazda yok — Faz 6'da (kamera varsayılan kapalı ilkesiyle) değerlendirilecek.
- `whatsapp.py` V2'de 15 KB (bazda 9.6 KB) — fark Faz 1'de incelenip güvenli parçalar alınacak.
- `requirements.txt` V2'de daha dolu (670 B vs 114 B) — birleştirilmiş liste `pyproject.toml`'da.

## D-04 — V3 (Mac) analizi: Windows'a taşınabilir olan/olmayan (2026-10-13, Faz 0)
- **Taşınamaz:** `calendar.py` (21 KB) ve Swift helper'lar macOS EventKit'e bağlı → Windows karşılığı **Google Calendar API** (Faz 3). `reminders.py` (9.6 KB) Apple Reminders'a bağlı → karşılığı Google Tasks/SQLite (Faz 3).
- **Taşınabilir:** Türkçe tarih yardımcıları (`TR_WEEKDAYS`, `TR_MONTHS`, `_add_months`, `_range_payload`) — Faz 3'te `datetime_utils`'a port edilecek. `jarvis_web/` Faz 5'te incelenecek.

## D-05 — USB sürücü kaybı ve C:'ye taşınma (2026-10-13, Faz 0)
`D:` bir USB sürücüydü, kullanıcı çıkardı; sürücü sistemden kayboldu. `D:\ultron`'daki tüm
Faz 0 işi + venv + legacy + kaynak zip erişilemez hale geldi. Proje `C:\ultron`'da sıfırdan
kuruluyor: iskelet dosyaları bu oturumun içeriğinden birebir yeniden yazıldı; `legacy/` ve
venv, kaynak zip (`jarvis-3.0.0-windows (1).zip`) yeniden temin edilince kurulacak.
Ders: ilk push geciktirilmemeli — bundan sonra her commit anında push'lanır.

## Açık sorular
- [ ] S-01: `LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"` güncel mi? API anahtarı olmadan doğrulanamaz. Faz 2 başında `live_config.py` içinde tek noktadan doğrulanacak.
- [ ] S-02: Google Cloud projesi (Gmail/Takvim OAuth) kullanıcı tarafından açılacak mı, mock ile mi ilerlenecek? (Faz 3'ü bloklar)
- [ ] S-03: Porcupine wake-word anahtarı var mı? Yoksa openWakeWord rotası (Faz 2).
