# PROGRESS.md — ULTRON Proje İlerleme Kaydı (TAM DEVİR BELGESİ)

> **Bu dosyanın amacı:** Yeni bir agent oturumu bu dosyayı okuyarak projenin TAMAMINI
> anlayabilsin ve kaldığı yerden hatasız devam edebilsin. Her şey burada: ortam,
> mimari, tüm commit'ler, kararlar, bilinen hatalar, sonraki adımlar.
>
> **Son güncelleme:** 2026-10-13 — Faz 2 tamamlandı, Faz 3 Google Calendar + Scheduler
> kodu yazıldı ve push'landı ama **Faz 3 REFACTOR'U YAPILMADI** — Faz 4'e geçmeden
> önce refactor ŞART (kullanıcı talimatı).
>
> **Tek doğruluk kaynağı spec:** `D:\ULTRON_MASTER_SPEC.md` (v1.0, 46.354 byte,
> SHA256 `C871BA62...A362BB`). Proje kökü dışında durur.

---

## 1. PROJE ÖZETİ (30 saniyede anla)

**ULTRON** — Windows'ta yaşayan, sesle ve yazıyla konuşan, gerçek işler yapan kişisel
yapay zekâ asistanı. Eski adı JARVIS olan bir projeyi (`jarvis-windows`) temel alarak,
spec'te tanımlanan 10 fazlı yol haritasıyla yeniden inşa ediliyor.

- **Kök:** `C:\ultron`
- **Git:** local repo + remote `https://github.com/emmggew-svg/ultron.git` (PRIVATE)
- **GitHub hesabı:** `emmggew-svg` (gh CLI ile giriş yapılmış, keyring'de token var)
- **Python:** 3.12.14 (venv: `C:\ultron\.venv`) — sistem Python'u 3.14'tür, KULLANILMAZ
- **Paket yöneticisi:** `uv 0.12.6` — `uv pip install --python C:\ultron\.venv\Scripts\python.exe <paket>`
- **Test:** `.\.venv\Scripts\python.exe -m pytest -q` → **96 passed** (Faz 3 itibarıyla)
- **Lint:** `uvx ruff check app/ tests/` → temiz

---

## 2. ORTAM ENVANTERİ (kesin değerler)

| Öğe | Değer |
|---|---|
| OS | Windows 10 build 19045 |
| Sistem Python | 3.14.7 (C:\Users\emmgg\AppData\Local\Python\pythoncore-3.14-64) |
| Proje Python | 3.12.14 (`uv` ile kuruldu) |
| venv | `C:\ultron\.venv` |
| uv | 0.12.6 (global) |
| git | 2.55.0.windows.3; `safe.directory` istisnası var (D:/ ve C:/ultron) |
| gh CLI | 2.96.0, hesap `emmggew-svg`, token keyring'de |
| GitHub repo | `emmggew-svg/ultron` (PRIVATE), branch: `main` |
| Spec dosyası | `D:\ULTRON_MASTER_SPEC.md` — proje kökü DIŞINDA |
| Kaynak zip | `jarvis-3.0.0-windows (1).zip` (10.841.543 byte) — kullanıcı USB'den temin etti |
| Live model | `gemini-2.5-flash-native-audio-preview-12-2025` (canlı sonda doğrulandı) |
| Live ses | `Charon` (Jarvis'in birebir sesi — kullanıcı şartıyla SABİT) |
| google-genai | 2.30.1 |

### Önemli komutlar
```powershell
cd C:\ultron
.\.venv\Scripts\python.exe -m pytest -q          # testler
uvx ruff check app/ tests/                        # lint
git add -A; git commit -m "..."; git push origin main  # her değişiklik push'lanır
```

### Dikkat edilmesi gerekenler
- Shell komutları PowerShell'de çalışır; `&&` KULLANMA (PowerShell 5.1 desteklemez),
  `;` ile ayır.
- Admin CMD'de çalıştırma — kullanıcı profili farklı olur (önce yaşandı).
- API anahtarları ASLA koda/loga/commit'e girmez (spec §5.7). Test anında
  `$env:GEMINI_API_KEY` ile geçici tanımlanır.

---

## 3. MİMARİ GENEL BAKIŞ

```
C:\ultron\
├─ app/
│  ├─ main.py                    # bootstrap (Faz 0'dan kalma; --check modu)
│  ├─ config/policy.yaml         # güvenlik politikası (default-deny + allowlist)
│  ├─ core/
│  │  ├─ events.py               # EventBus (pub/sub)
│  │  └─ prompts/system.md       # ULTRON sistem promptu (Türkçe, güvenlik odaklı)
│  ├─ memory/
│  │  ├─ __init__.py
│  │  └─ store.py                # atomik JSON hafıza (thread-safe, hassas bilgi reddi)
│  ├─ security/
│  │  ├─ policy.py               # PolicyEngine: path/shell/tool kararları
│  │  ├─ confirm.py              # onay akışı (timeout→red, killswitch→red)
│  │  ├─ audit.py                # hash-zincirli SQLite audit log
│  │  ├─ killswitch.py           # global durdurma
│  │  └─ secrets.py              # keyring sarmalayıcı (Windows Credential Manager)
│  ├─ tools/
│  │  ├─ registry.py             # @tool dekoratörü + ToolResult + ToolRegistry
│  │  ├─ loader.py               # load_all() — tüm araç modüllerini import eder
│  │  ├─ system_tools.py         # sys_info, app_open
│  │  ├─ web_tools.py            # browser_open, get_weather
│  │  ├─ shell_tool.py           # shell_run (allowlist, HIGH)
│  │  ├─ comms_tools.py          # save_whatsapp_contact, send_whatsapp_message
│  │  ├─ memory_tools.py         # save_memory, delete_memory
│  │  ├─ task_tools.py           # calendar_list/create/delete, add/get_reminders (FAZ1 placeholder)
│  │  ├─ google_calendar.py      # OAuth + calendar_list/create/delete (GERÇEK API)
│  │  └─ scheduler.py            # APScheduler + reminder_add/list/delete (GERÇEK zamanlayıcı)
│  └─ voice/
│     ├─ live_config.py          # LIVE_MODEL, VOICE_NAME=Charon, örneklem oranları
│     ├─ audio_io.py             # tek PyAudio sahibi (B-18 çözümü)
│     ├─ live_session.py         # LiveSessionManager (B-07/B-08/B-09 çözümleri)
│     └─ wakeword.py             # ClapBackend + WakeWordDetector
├─ legacy/                       # SALT-OKUNUR referans (asla değiştirilmez)
│  ├─ jarvis-windows/            # baz kod tabanı (Analiz B-01…B-20 buradan)
│  ├─ v2-windows/                # genişletilmiş V2 (tool_defs.py vs)
│  └─ v3-mac/                    # Mac sürümü (EventKit — taşınamaz)
├─ tests/
│  ├─ test_faz0_sanity.py        # 5 test
│  ├─ test_registry.py           # 9 test
│  ├─ test_policy.py             # 16 test
│  ├─ test_confirm.py            # 6 test
│  ├─ test_secrets.py            # 5 test
│  ├─ test_shell_tool.py         # 7 test
│  ├─ test_system_web_tools.py   # 7 test
│  ├─ test_comms_tools.py        # 5 test
│  ├─ test_memory.py             # 3 test
│  ├─ test_task_tools.py         # 4 test
│  ├─ test_voice.py              # 16 test
│  ├─ test_scheduler.py          # 2 test
│  └─ safety/
│     ├─ test_injection.py       # 4 test
│     ├─ test_audit_chain.py     # 4 test
│     └─ test_privacy.py         # 3 test
├─ scripts/
│  └─ live_smoke.py              # canlı bağlantı testi (KULLANICI koşturur)
├─ docs/
│  ├─ RUNBOOK.md                 # elle test talimatları
│  └─ TOOLS.md                   # araç kataloğu
├─ DECISIONS.md                  # D-01…D-08 kararlar
├─ CHANGELOG.md                  # sürüm notları
├─ HANDOFF.md                    # devir belgesi (Faz 0 itibarıyla, güncel değil)
├─ PROGRESS.md                   # BU DOSYA
├─ pyproject.toml                # 15 bağımlılık + ruff config
├─ .gitignore, .gitattributes
└─ README.md
```

### Kayıtlı 19 araç (loader.load_all() ile)

| Araç | Risk | Onay | Açıklama |
|---|---|---|---|
| `sys_info` | SAFE | auto | pil/CPU/RAM/disk/saat/tarih/ağ |
| `get_weather` | SAFE | auto | wttr.in özeti (untrusted işaretli) |
| `calendar_list` | SAFE | auto | Google Calendar listeleme (GERÇEK API) |
| `reminder_list` | SAFE | auto | yerel hatırlatıcı listesi |
| `app_open` | LOW | auto | takma adlı uygulama açma |
| `browser_open` | LOW | auto | URL açma / arama / YouTube |
| `save_memory` | LOW | auto | hassas bilgi reddedilir, atomik yazım |
| `delete_memory` | LOW | auto | category/key veya metin eşleşmesi |
| `get_calendar_events` | LOW | auto | takvim sayfası açar (FAZ 1 placeholder, gerisi Faz 3'te) |
| `get_reminders` | LOW | auto | yerel hatırlatıcı listesi (FAZ 1 placeholder) |
| `add_calendar_event` | MEDIUM | auto | şablon URL (FAZ 1 placeholder) |
| `add_reminder` | MEDIUM | auto | FAZ 1 placeholder |
| `calendar_create` | MEDIUM | auto | Google Calendar etkinlik oluştur (GERÇEK) |
| `reminder_add` | MEDIUM | auto | APScheduler hatırlatıcı (GERÇEK) |
| `reminder_delete` | MEDIUM | auto | APScheduler sil |
| `save_whatsapp_contact` | MEDIUM | auto | rehber kaydı (atomik) |
| `calendar_delete` | HIGH | CONFIRM | Google Calendar sil |
| `send_whatsapp_message` | HIGH | CONFIRM | alıcı doğrulamalı; pencere-doğrulama Faz 6 |
| `shell_run` | HIGH | CONFIRM | allowlist + parser; onaysız çalışmaz |

**ÖNEMLİ:** `task_tools.py` içindeki `add_calendar_event`, `get_calendar_events`,
`add_reminder`, `get_reminders` **FAZ 1 placeholder'larıdır** (şablon URL + yerel JSON).
Faz 3'te GERÇEK karşılıkları geldi: `calendar_list/create/delete` (google_calendar.py)
ve `reminder_add/list/delete` (scheduler.py). **ÇAKIŞMA VAR** — refactor'ta
placeholder'lar ya silinecek ya da gerçek API'lere redirect edilecek.

---

## 4. YAPILAN İŞ — COMMIT COMMIT (tarihçe)

### FAZ 0 — Hazırlık (commit: `6568e16`)
- Proje iskeleti, `.gitignore` (spec §5.7), `pyproject.toml` (3.12 pin, 15 bağımlılık)
- `legacy/` altına 3 referans paket çıkarıldı (jarvis-windows, v2-windows, v3-mac)
- **B-01…B-20 doğrulama tablosu** yazıldı (`DECISIONS.md` D-02) — dosya:satır kanıtı
- Python 3.12 venv kurulumu, v2 `tool_defs.py` + `webcam_vision.py` porta işaretlendi
- `launch.json` temizliği (B-11 — gömülü kullanıcı yolu kalktı)
- Kabul: `python -m app.main --check` → CHECK OK, 5 test yeşil

### FAZ 1 — Güvenlik İskeleti (commit: `57c8fd6` → `0c9ba8c`, 12 commit)
**faz-1a** (`57c8fd6`): Tool Registry + `ToolResult` + `@tool` dekoratörü
- `app/tools/registry.py` — Risk enum, ToolDef, Gemini şema otomatik üretimi
- `tests/test_registry.py` — 9 test (duplicate red, unknown red, ok-alanı kararı)
- **B-15 kapandı**: hata tespiti `ok` alanı ile (kelime-avı değil)
- **B-19 kapandı**: elif zinciri yok, her araç tek dosyada

**faz-1b** (`19ed93e`): Policy Engine + Audit + KillSwitch
- `app/security/policy.py` — allowlist shell, path kararları, chain escalation
- `app/security/audit.py` — SQLite + hash zinciri (prev_hash + sha256)
- `app/security/killswitch.py` — global durdurma
- `app/config/policy.yaml` — default-deny + allowed_commands listesi
- `tests/test_policy.py` — 16 test
- **B-05 kapandı**: kara liste yerine allowlist + parser

**faz-1c** (`68bcd3f`): Onay çekirdeği
- `app/security/confirm.py` — `request_approval()`, timeout→red, killswitch→red
- `tests/test_confirm.py` — 6 test

**faz-1d** (`b74c3e3`): keyring sır yönetimi
- `app/security/secrets.py` — Windows Credential Manager sarmalayıcı
- `migrate_legacy()` — eski `api_keys.json` içe aktar-sil
- `tests/test_secrets.py` — 5 test (gerçek Credential Manager turu)
- **B-16 kapandı**: düz metin anahtar dosyası ÖLÜ

**faz-1e** (`192ccca`): shell_run aracı
- `app/tools/shell_tool.py` — allowlist aracı, HIGH + CONFIRM
- `tests/test_shell_tool.py` — 7 test

**faz-1f** (`33e7a2b`): SAFE/LOW araçlar portu
- `app/tools/system_tools.py` — sys_info, app_open
- `app/tools/web_tools.py` — browser_open, get_weather (B-13: macOS UA temizlendi)
- `tests/test_system_web_tools.py` — 7 test

**faz-1g** (`0e592ea`): WhatsApp araçları
- `app/tools/comms_tools.py` — save_whatsapp_contact, send_whatsapp_message
- HIGH + CONFIRM: registry kapısı onaysız gövdeye girişi engeller
- `tests/test_comms_tools.py` — 5 test
- **B-06 kısmen kapandı** (D-06: pencere doğrulaması Faz 6'ya)

**faz-1h** (`828ddf4`): Atomik hafıza
- `app/memory/store.py` — tmp+replace yazım, thread kilit, hassas bilgi reddi
- `app/tools/memory_tools.py` — save_memory, delete_memory
- `tests/test_memory.py` — 3 test
- **B-17 kapandı**

**faz-1i** (`6307437`): Takvim/görev placeholder'ları
- `app/tools/task_tools.py` — şablon URL + yerel JSON (FAZ 1 SEVİYESİ, Faz 3'te değişecek)
- `tests/test_task_tools.py` — 4 test
- **B-03 kısmen kapandı** (tarih matematiği)

**faz-1j** (`35deaa6`): Ultron sistem promptu
- `app/core/prompts/system.md` — Türkçe, güvenlik bölümü değiştirilemez
- **B-04 kapandı**: macOS kalıntıları temizlendi

**faz-1k** (`2e1c02f`): safety paketi
- `tests/safety/test_injection.py` — zararlı mail → onaysız eylem YOK
- `tests/safety/test_audit_chain.py` — kurcalama tespiti + redaksiyon
- `tests/safety/test_privacy.py` — sır kalıbı taraması, örnek config'ler boş

**faz-1l** (`0c9ba8c`): Belgeler — TOOLS.md, CHANGELOG, DECISIONS güncelleme

**REFACTOR 1** (`3b9c358`, `c887072`): ruff temizliği (603→0), StrEnum, loader modülü
- `app/tools/loader.py` — `load_all()` ile merkezi import (unutma sınıfı kapandı)

### FAZ 2 — Ses Katmanı (commit: `3b8ecbb` → `db90d1d`)

**faz-2a** (`3b8ecbb`): Ses sabitleri + AudioIO + EventBus
- `app/voice/live_config.py` — LIVE_MODEL, VOICE_NAME="Charon", 16kHz/24kHz
- `app/voice/audio_io.py` — tek PyAudio sahibi, subscribe/unsubscribe, flush_output()
- `app/core/events.py` — EventBus
- **B-18 kapandı**: çift PyAudio yok, herkes abone

**faz-2b** (`5b8994c`): LiveSessionManager + WakeWord
- `app/voice/live_session.py` — resumption (tutamaç saklama), barge-in (flush_output),
  araçlar semaphore-sınırlı arka planda, GoAway anında reconnect
- `app/voice/wakeword.py` — ClapBackend + WakeWordDetector (IDLE/ACTIVE durum makinesi)
- `tests/test_voice.py` — 16 test (sahte oturum ile, donanım gerektirmez)
- **B-07/B-08/B-09 kapandı**

**faz-2c** (`3070005`): RUNBOOK elle test talimatları + D-08 kararı

**faz-2d** (`38cb53b`): `scripts/live_smoke.py` — canlı bağlantı testi scripti
- Kullanıcı `GEMINI_API_KEY` env ile koşturur

**faz-2e** (`8c53c0c`): Canlı sonda doğrulaması
- **S-01 KAPANDI**: `gemini-3.8-live` 1007 yiyor (erişim yok); çalışan model
  **`gemini-2.5-flash-native-audio-preview-12-2025`** — `live_config.py` güncellendi
- **Charon doğrulandı**: canlı sondada Charon sesiyle ses parçası alındı
- Üretim config (13 araç) uçtan uca çalıştı: model `sys_info` aracını çağırdı
- **SDK bug çözüldü**: `SlidingWindow` çıplak verilemez → `ContextWindowCompressionConfig(sliding_window=...)`

**refactor** (`db90d1d`): `_send_loop` timeout + `AudioIO.close()` temiz kapatma

### FAZ 3 — Google Calendar + Zamanlayıcı (commit: `ee78374`, `ec61a44`)

**faz-3** (`ee78374`):
- `app/tools/google_calendar.py` — OAuth (gohu token.json) + calendar_list/create/delete
  - 3 yeni tool: `calendar_list` (SAFE), `calendar_create` (MEDIUM), `calendar_delete` (HIGH+CONFIRM)
- `app/tools/scheduler.py` — APScheduler + SQLite jobstore + JSON kalıcılık
  - 3 yeni tool: `reminder_add` (MEDIUM), `reminder_list` (SAFE), `reminder_delete` (MEDIUM)
  - `SchedulerManager` — kaçırılan hatırlatıcıları açılışta ateşleyen thread
  - `win10toast` ile Windows toast bildirimleri
- `app/tools/loader.py` güncellendi — yeni modüller import ediliyor
- `pyproject.toml` — apscheduler, win10toast eklendi
- `tests/test_scheduler.py` — 2 test
- Yeni bağımlılıklar: `apscheduler==3.10.4`, `win10toast==0.9`, `sqlalchemy==2.1.4`,
  `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`

**fix** (`ec61a44`): Scheduler APScheduler serialization hatası + timezone + static fire method

**Sorunlar (ÇÖZÜLDÜ):**
1. `SlidingWindow` çıplak verilemez → `ContextWindowCompressionConfig(sliding_window=...)` (SDK 2.30.1)
2. `timezone="local"` Windows'ta pytz hata verir → `timezone="UTC"`
3. APScheduler instance method pickle edemez → static method kullan
4. SQLAlchemy eksikti → kuruldu

---

## 5. KARARLAR (DECISIONS.md özeti — detay orada)

| ID | Karar | Durum |
|---|---|---|
| D-01 | Baz = `legacy/jarvis-windows/` | ✅ |
| D-02 | B-01…B-20 doğrulama (19 tam + 1 kısmen) | ✅ |
| D-03 | V2 farkları analiz edildi | ✅ |
| D-04 | V3'ten taşınabilir parçalar belirlendi | ✅ |
| D-05 | USB D: kayboldu → C:'ye taşındı | ✅ |
| D-06 | WhatsApp pencere doğrulaması Faz 6'ya ertelendi | ⏳ |
| D-07 | Ruff: BLE001/S110/S112/RUF001-003/E501 kapalı (bilinçli) | ✅ |
| D-08 | Live model + Charon canlı sonda ile doğrulandı | ✅ |

### Açık sorular
- **S-01**: ✅ KAPANDI (D-08)
- **S-02**: Google Cloud projesi OAuth credentials.json kullanıcıdan bekleniyor
  (Faz 3'ün gerçek kullanımı için ŞART — kod hazır, kullanıcı sadece
  `app/data/google/credentials.json` koymalı)
- **S-03**: Porcupine wake-word anahtarı (şu an çift-alkış yedeği aktif)

---

## 6. BİLİNEN SORUNLAR / TEKNİK BORÇ

### Faz 3 Refactor İHTİYACI (kullanıcı talimatı — ŞART)
1. **`task_tools.py` ile `google_calendar.py` çakışması**: 4 FAZ-1 placeholder tool
   (`add_calendar_event`, `get_calendar_events`, `add_reminder`, `get_reminders`)
   ile Faz 3'teki 6 gerçek tool (`calendar_list/create/delete`, `reminder_add/list/delete`)
   aynı işi farklı seviyelerde yapıyor. **Placeholder'lar silinecek veya redirect edilecek.**
2. `scheduler.py` içinde `_SCHEDULER` global singleton — thread-safety gözden geçirilmeli
3. `google_calendar.py` OAuth token dosyası `app/data/google/` altında — gitignore kontrolü
4. `app/data/` klasörü `.gitignore`'da YOK — scheduler.sqlite ve reminders.json commit'e girmiş olabilir
5. `SchedulerManager._check_missed` thread'i 30 sn'de bir çalışıyor — daha verimli yapılabilir
6. Test `test_reminder_roundtrip` 3 saniye sleep içeriyor — flaky olabilir

### Diğer bilinen sorunlar
- `app/main.py` hâlâ Faz 0 bootstrap'u — ULTRON çekirdeği (`ultron_agent.py` gibi)
  hâlâ yok. Faz 7'de Planner/Executor/Verifier yazılacak.
- Wake-word aktif değil (çift-alkış backend var ama canlı smoke testinde kullanılmıyor)
- S-02: Google Cloud OAuth credentials.json kullanıcıdan bekleniyor
- S-03: Porcupine anahtarı yoksa openWakeWord rotası

---

## 7. SONRAKİ ADIMLAR (öncelik sırasıyla)

### HEMEN YAPILACAK (bu oturumda)
1. **Faz 3 REFACTOR** — kullanıcının talimatı:
   - `task_tools.py`'daki 4 placeholder tool'u SİL (gerçekleri Faz 3'te geldi)
   - `tests/test_task_tools.py`'ı gerçek API'lerle senkronize et
   - `app/data/` klasörünü `.gitignore`'a ekle (sqlite + json artıkları)
   - `DECISIONS.md`'ye D-09 kararı ekle (placeholder → gerçek API geçişi)
   - `docs/TOOLS.md` güncelle (19 araç tablosu)
   - ruff + pytest → temiz
2. **Faz 4 — Gmail** (spec §6.3):
   - `app/tools/gmail_tools.py` — arama/okuma/özet + taslak + ONAYLI gönderim
   - Sırlar keyring'e (`gmail_credentials`)
   - Direkt gönderme YOK; her gönderim confirm kapısından geçer
   - Günlük limit: 20 mail (policy.yaml)
   - `tests/test_gmail_tools.py`

### Faz 5-9 (sırayla)
- **Faz 5**: Dosya/Web — undo, dry-run, Playwright izole profil
- **Faz 6**: Bilgisayar kontrolü — UIA > pyautogui > görsel döngü, WhatsApp pencere doğrulaması
- **Faz 7**: Planner/Executor/Verifier + 4 katmanlı hafıza + proaktiflik
- **Faz 8**: Spotify/Telegram/MCP/Ollama
- **Faz 9**: UI bölünmesi + Ultron teması + tray + sihirbaz + install.ps1

---

## 8. YENİ OTURUM İÇİN HIZLI BAŞLANGIÇ

```powershell
# 1. Repo kontrolü
cd C:\ultron
git status                                    # temiz olmalı
git log --oneline -5                          # ec61a44 fix: scheduler...

# 2. Testler
.\.venv\Scripts\python.exe -m pytest -q       # 96 passed bekleniyor

# 3. PROGRESS okunduktan sonra:
# → Bölüm 7'deki "HEMEN YAPILACAK" adımlarını takip et
# → Faz 3 refactor + Faz 4 Gmail

# 4. Her değişiklikte
git add -A
git commit -m "faz-3-r: refactor — placeholder silme"
git push origin main
```

### Yeni oturumda ÖNEMLİ bağlam
- Kullanıcı Türkçe konuşur, samimi ton kullanır ("aslanım", "kardeşim" vb.)
- Her commit ANINDA push'lanır (D-05 dersi)
- Test yazılmadan feature YOK (spec §12 Definition of Done)
- Güvenlik pazarlıksız (spec §5)
- `legacy/` klasörüne ASLA dokunulmaz (salt-okunur referans)
- API anahtarları koda yazılmaz; test anında `$env:` ile geçici tanımlanır
- Her faz bitiminde CHANGELOG.md güncellenir

---

## 9. DOSYA İÇERİĞİ İNDEKSİ (hızlı erişim)

| Dosya | Satır | İçerik |
|---|---|---|
| `app/tools/registry.py` | 237 | ToolRegistry, ToolDef, ToolResult, Risk, @tool |
| `app/tools/loader.py` | 20 | load_all() — 7 modül import |
| `app/tools/system_tools.py` | 140 | sys_info, app_open |
| `app/tools/web_tools.py` | 118 | browser_open, get_weather |
| `app/tools/shell_tool.py` | 80 | shell_run (allowlist) |
| `app/tools/comms_tools.py` | 180 | WhatsApp save/send |
| `app/tools/memory_tools.py` | 85 | save/delete_memory |
| `app/tools/task_tools.py` | 170 | calendar/reminder PLACEHOLDER (Faz 1) |
| `app/tools/google_calendar.py` | 210 | OAuth + calendar_list/create/delete (Faz 3) |
| `app/tools/scheduler.py` | 210 | APScheduler + reminder_add/list/delete (Faz 3) |
| `app/security/policy.py` | 190 | PolicyEngine |
| `app/security/audit.py` | 130 | hash-zincirli SQLite |
| `app/security/confirm.py` | 85 | onay çekirdeği |
| `app/security/killswitch.py` | 55 | global durdurma |
| `app/security/secrets.py` | 95 | keyring sarmalayıcı |
| `app/memory/store.py` | 90 | atomik hafıza |
| `app/tools/memory_tools.py` | 85 | save/delete memory |
| `app/core/events.py` | 35 | EventBus |
| `app/voice/live_config.py` | 45 | model+ses sabitleri |
| `app/voice/audio_io.py` | 145 | tek PyAudio sahibi |
| `app/voice/live_session.py` | 200 | LiveSessionManager |
| `app/voice/wakeword.py` | 95 | WakeWordDetector |

---

## 10. TEST DURUMU (son koşu: 2026-10-13)

```
============================= test session starts =============================
collected 96 items

tests/test_comms_tools.py .....          [  5%]
tests/test_confirm.py ......             [ 11%]
tests/test_faz0_sanity.py .....          [ 16%]
tests/test_memory.py ...                 [ 19%]
tests/test_policy.py ................    [ 36%]
tests/test_registry.py .........         [ 45%]
tests/test_scheduler.py ..               [ 47%]
tests/test_secrets.py .....              [ 53%]
tests/test_shell_tool.py .......         [ 60%]
tests/test_system_web_tools.py .......   [ 67%]
tests/test_task_tools.py ....            [ 71%]
tests/test_voice.py ................     [ 88%]
tests/safety/test_audit_chain.py ....    [ 93%]
tests/safety/test_injection.py ....      [ 97%]
tests/safety/test_privacy.py ...         [100%]

============================== 96 passed ==============================
```

---

## 11. GITHUB REPO DURUMU

- **Repo:** https://github.com/emmggew-svg/ultron (PRIVATE)
- **Branch:** `main`
- **Son commit:** `ec61a44 fix: scheduler APScheduler serialization + timezone + static fire method`
- **Toplam commit:** 24 (Faz 0'dan Faz 3'e)
- **Çalışma ağacı:** temiz

---

*Bu belge ULTRON projesinin tam geçmişini içerir. Yeni oturumda okuyan agent
kaldığı yerden (Bölüm 7: Faz 3 refactor → Faz 4 Gmail) devam eder.*
