# ULTRON — DEVİR / HANDOFF BELGESİ (v2 — C:\ultron)

> **Amaç:** Bu dosya, ULTRON projesini başka bir makinede / başka bir sürücüde /
> başka bir kodlama-ajanı oturumunda kaldığı yerden devam ettirmek için gereken
> HER ŞEYİ içerir. Tek doğruluk kaynağı spec: `ULTRON_MASTER_SPEC.md` (v1.0).
> Son güncelleme: 2026-10-13 ~21:05 (Faz 0 — C: üzerinde yeniden kurulum).

## 0. 30 SANİYELİK ÖZET

- **Proje:** ULTRON — Windows'ta yaşayan kişisel süper asistan (Python 3.12, yerel).
- **Kök:** `C:\ultron` (önce `D:\ultron` idi; D: bir USB sürücüydü, çıkarıldı ve kayboldu — bk. §10.1).
- **Git:** depo hazır, remote `origin = https://github.com/emmggew-svg/ultron.git` (private repo AÇIK ama BOŞ — push henüz yok).
- **Baz kod:** `legacy/jarvis-windows/` — **HENÜZ YOK**, kaynak zip bekleniyor (`jarvis-3.0.0-windows (1).zip`).
- **venv:** **HENÜZ YOK** — zip ile birlikte kurulacak.
- **Durum:** Faz 0 + Faz 1 TAMAMLANDI (78 test yeşil, 12 commit push'lu).
  Sıradaki: Faz 2 (ses katmanı). S-01 (model adı) Faz 2'nin ilk işi.
- **Kural:** Faz N bitmeden Faz N+1'e başlama. Güvenlik (spec §5) pazarlıksız. Her commit anında push.
- **Kural:** Faz N bitmeden Faz N+1'e başlama. Güvenlik (spec §5) pazarlıksız. Her commit anında push (ders: §10.1).

## 1. ORTAM ENVANTERİ (doğrulanmış)

| Öğe | Değer |
|---|---|
| İşletim sistemi | Windows 10 build 19045 |
| Sistem Python'u | 3.14.7 (proje KULLANMAZ) |
| Proje Python'u | **3.12.14**, `uv` ile kurulur: `uv python install 3.12` |
| venv hedefi | `C:\ultron\.venv` → `C:\ultron\.venv\Scripts\python.exe` |
| Paket yöneticisi | `uv 0.12.6` (global). NOT: `uv pip index` YOK; venv'te `pip` modülü YOK — kurulum: `uv pip install --python C:\ultron\.venv\Scripts\python.exe ...` |
| git | 2.55.0. `safe.directory` istisnaları eklendi (D: ve C: kökleri için). Yeni kökte tekrar gerekir: `git config --global --add safe.directory <kök>` |
| GitHub CLI | `gh 2.96.0`, hesap `emmggew-svg` (keyring, `repo` scope) |
| GitHub repo | `emmggew-svg/ultron` — **PRIVATE, ŞU AN BOŞ**. URL: `https://github.com/emmggew-svg/ultron` |
| Varsayılan dal | `main` yapılacak: `git branch -M main`, ilk push `git push -u origin main` |
| Kaynak zip | `jarvis-3.0.0-windows (1).zip` (10.841.543 byte) — ORİJİNALE DOKUNULMAZ, repoya girmez (`*.zip` gitignore'da) |
| Spec | `ULTRON_MASTER_SPEC.md` v1.0 (46.354 byte) — proje dışında tutulur |

## 2. KİLİTLENMİŞ KARARLAR (kullanıcı onaylı)

1. Proje kökü `C:\ultron` (bu dosyadaki tüm yollar buna göre; taşınırsa toplu değiştir).
2. Baz = küçük `jarvis-windows.zip`; V2'den `tool_defs.py` + `webcam_vision.py` porta dahil; gerisi özgün, sıfır-kusur hedefli.
3. Python 3.12, `uv` ile pinli venv.
4. Her commit anında GitHub'a push (`emmggew-svg/ultron`, private).
5. Lisans (spec §14): "Alp Ünlü — @alppunlu" atfı korunur; kişisel kullanım serbest, yayın/satışta izin veya yeniden yazım. "Ultron" adı kişisel tema olarak kalır.

## 3. DOSYA HARİTASI (hedef durum — legacy/ ve .venv zip sonrası oluşacak)

```
C:\ultron\
├─ .git/                  depo (remote origin TANIMLI, commit YOK)
├─ .venv/                 [EKSİK — §7.3'te kurulacak]
├─ .vscode\launch.json    TEMİZ ✔ (yazıldı)
├─ .gitignore             spec §5.7 + Python ✔ (legacy/*/memory/ dışlanmaz!)
├─ pyproject.toml         ==3.12.*, 9 bağımlılık + pytest ✔ (freeze §7.5'te)
├─ app\__init__.py ✔, app\main.py ✔ (--check + GEÇİCİ legacy köprü)
├─ tests\test_faz0_sanity.py ✔ (5 test)
├─ docs\RUNBOOK.md ✔
├─ DECISIONS.md ✔ (D-01…D-05, B-tablosu, S-01…S-03)
├─ CHANGELOG.md ✔, README.md ✔, HANDOFF.md ✔ (bu dosya)
└─ legacy\               [EKSİK — §7.2'de çıkarılacak] SALT-OKUNUR REFERANS:
   ├─ jarvis-windows\     BAZ (main.py 40.572 B, ui.py 89.572 B, 13 action, prompt, memory)
   ├─ v2-windows\         tool_defs.py (17 KB, Türkçe karakterler BOZUK/mojibake),
   │                      webcam_vision.py (7.5 KB), whatsapp.py (15 KB), SFX/, Fonts/
   └─ v3-mac\             calendar.py 21 KB (EventKit — TAŞINAMAZ), reminders.py 9.6 KB (TAŞINAMAZ),
                          taşınabilir: TR_WEEKDAYS/TR_MONTHS/_add_months/_range_payload, jarvis_web/
```

## 4. KURULACAK PAKETLER (önceki oturumda 10/10 OK idi)

`google-genai`, `SpeechRecognition`, `pyaudio` (tekerlek var), `psutil`, `Pillow`,
`requests`, `pyperclip`, `mss`, `pyautogui`, `pytest`.
```powershell
uv pip install --python C:\ultron\.venv\Scripts\python.exe google-genai SpeechRecognition pyaudio psutil Pillow requests pyperclip mss pyautogui pytest
```
NOT: iki `uv pip` ÇAKIŞTIRILMAZ (os error 87/433 verir) — tek seferde tek kurulum.
`pytest` yarım kurulursa (`_pytest.__version__` hatası): `--force-reinstall pytest`.

## 5. B-01…B-20 ÖZETİ (detay: DECISIONS.md D-02)

19 DOĞRULANDI, 1 kısmen (B-14: dump var, "İngilizce zorlama" bulunamadı).
Kritikler: B-05 (kara liste + `shell=True`), B-06 (kör `Enter`; prompt satır 10 teşvik ediyor),
B-16 (düz-metin `api_keys.json`). Ek: `weather.py:23` "JARVIS macOS" user-agent'ı.
`_interrupt_audio` hiç çağrılmıyor; mikrofon konuşurken kapalı (`main.py:874-875`);
araçlar receive döngüsünde `await`leniyor (`main.py:945-952`).

## 6. GEÇMİŞ SORUŞTURMA NOTU (kapanmış sayılır)

Önceki oturumda `--check` iki kez asılı kaldı; izolasyon 4 import'u akladı, 5. grup
`pytest`'in bozuk kurulumuna takıldı. Son koşuda `--check` **GEÇTİ** (`CHECK OK`) —
asılmalar geçiciydi (çakışan koşular + D: sürücüsünün ölmesi). Yeni kurulumda
`--check` geçmezse önce `§10.2` işletilir, kod değiştirilmez.

## 7. KALAN FAZ 0 ADIMLARI (sırayla)

```powershell
# ÖNKOŞUL: kaynak zip C:\ kökünde (kullanıcı koyar) → örn. C:\jarvis-3.0.0-windows (1).zip
cd C:\ultron
# 7.1 venv
uv venv --python 3.12 .venv
# 7.2 legacy çıkarma (iç zip adları: 'Windows/jarvis-windows.zip', 'JARVIS V2 WINDOWS.zip', 'MacOS - JARVIS V3.zip';
#     hedefler: legacy/jarvis-windows, legacy/v2-windows, legacy/v3-mac; ara klasörler ve __MACOSX artıkları temizlenir)
# 7.3 paketler (§4 komutu)
# 7.4 doğrulama
.\.venv\Scripts\python.exe -m app.main --check     # CHECK OK beklenir
.\.venv\Scripts\python.exe -m pytest -q            # 5/5 yeşil beklenir
# 7.5 HUD açılışı (gözle: legacy pencere + API-key ekranı; ANAHTAR GİRME)
.\.venv\Scripts\python.exe -m app.main
# 7.6 freeze → pyproject.toml dependencies'e sabitle
# 7.7 ilk commit + push
git add -A; git status --short
git commit -m "faz-0: hazirlik — iskelet, legacy referans, B-listesi dogrulama"
git branch -M main; git push -u origin main
# 7.8 kabul: CHECK OK + pytest yeşil + HUD + push GitHub'da görünüyor
```
7.8 olmadan Faz 1'e başlanmaz. Sonraki commitler `faz-1: ...` önekli, her biri push'lanır.

## 8. FAZ PLANI (özet — detay spec §11'de)

Faz 1 güvenlik iskeleti (Registry, policy, confirm, audit, killswitch, keyring, safety testleri) →
Faz 2 ses → Faz 3 takvim/görev → Faz 4 Gmail → Faz 5 dosya/web → Faz 6 bilgisayar kontrolü →
Faz 7 beyin+hafıza → Faz 8 genişleme → Faz 9 teslim.

## 9. AÇIK SORULAR (kullanıcıya)

- S-01: Live model adı güncel mi? (Faz 2, anahtarla)
- S-02: Google Cloud projesi açılacak mı, mock mu? (Faz 3'ü bloklar)
- S-03: Porcupine anahtarı var mı, openWakeWord mi? (Faz 2)

## 10. BİLİNEN ORTAM SORUNLARI + ÇÖZÜMLERİ

1. **USB-D kayboldu (2026-10-13):** os error 433 + python.exe kaybolması + "Working directory does not exist: D:\"
   ile teşhis edildi; `Get-Volume`'da D: yok. Çözüm: projeyi C:'ye taşı (yapıldı). Ders: erken push.
2. **Shell takılması:** asılı `gh.exe` + stale `.git/config.lock` (197 B). Çözüm: `taskkill /F /IM gh.exe`,
   lock'u sil, `opencode service restart`. Ön-plan takılırsa `background:true` + çıktı dosyasından oku.
3. **Dubious ownership:** her yeni kökte `git config --global --add safe.directory <kök>`.
4. **Defender:** proje kökü dışlama listesine eklenmeli.
5. **uv 0.12.6'da `pip index` yok; venv'te `pip` yok** — hep `uv pip ... --python <venv-python>`.
6. **Sırlar:** anahtar/token ASLA koda, loga, commit'e, bu dosyaya girmez. Gerçek anahtarlar Faz 1'de keyring'e.

*— v2: C: üzerinde yeniden kurulum oturumu. Sonraki oturum §7 sırasını izlesin.*
