# CHANGELOG.md — ULTRON

## [0.3.1] — Faz 3 refactor (2026-10-13)
- `task_tools.py` placeholder'ları SİLİNDİ (4 tool) — yerine Faz 3'te gerçek
  Google Calendar + APScheduler araçları geldi. Toplam araç: 19 → 15.
- `.gitignore`'a `app/data/` eklendi (scheduler.sqlite, reminders.json).
- DECISIONS.md'ye D-09 kararı eklendi. TOOLS.md güncellendi.
- Test: 96 → 92 (4 placeholder testi silindi, tümü yeşil).

## [0.3.0] — Faz 3 + Faz 2 (2026-10-13)
- Ses sabitleri: model `gemini-3.8-live`, ses **Charon** (mühürlü).
- Tek `AudioIO` sahibi, event bus, Live oturum yöneticisi (resumption+barge-in),
  wake-word durum makinesi (çift-alkış yedeği).

## [0.2.0] — Faz 1 (tamamlandı, 2026-10-13)
- Tool Registry + `ToolResult` (B-15/B-19 kapandı). 13 araç registry'de.
- Policy Engine (allowlist) + audit (hash zinciri) + kill switch + confirm çekirdeği (B-05).
- keyring sır yönetimi + legacy taşıyıcı (B-16).
- Araç portları: shell_run, sys_info, app_open, browser, weather (B-13), WhatsApp (B-06 kısmi, D-06),
  hafıza (B-17), takvim/görev (B-03 kısmi), Ultron promptu (B-04).
- Kabul: 78 test yeşil (safety dahil); HIGH onaysız çalışmaz; logda sır yok.
- Tool Registry + `ToolResult` (B-15/B-19 kapandı).
- Policy Engine (allowlist) + audit (hash zinciri) + kill switch + confirm çekirdeği (B-05).
- keyring sır yönetimi + legacy taşıyıcı (B-16).
- Araç portları: shell_run, sys_info, app_open, browser, weather (B-13), WhatsApp (B-06 kısmi, D-06),
  hafıza (B-17), takvim/görev (B-03 kısmi), Ultron promptu (B-04).

## [0.1.0] — Faz 0 (tamamlandı)
- Proje kökü önce `D:\ultron` (USB sürücü çıkarıldı, sürücü kayboldu) → **`C:\ultron`**'a taşındı.
- Git deposu + GitHub private repo (`emmggew-svg/ultron`) + remote hazır; ilk commit Faz 0 kabulünden sonra.
- `legacy/` referans paketleri kaynak zip'ten yeniden çıkarılacak (zip bekleniyor).
- B-01…B-20 doğrulaması tamamlandı (`DECISIONS.md` D-02); B-04/B-13'te ek bulgular.
- Python 3.12 venv (`uv`), `pyproject.toml`, `.gitignore` (spec §5.7).
