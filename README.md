# ULTRON — Kişisel Süper Asistan

Windows'ta yaşayan, sesle ve yazıyla konuşulan, gerçek işler yapan kişisel asistan.
Tek doğruluk kaynağı: spec `ULTRON_MASTER_SPEC.md` (proje dışında tutulur).
Devir belgesi: [`HANDOFF.md`](HANDOFF.md).

## Durum
Faz 0 — Hazırlık (bk. `CHANGELOG.md`, `DECISIONS.md`).

## Hızlı başlangıç
```powershell
uv venv --python 3.12 .venv
uv pip install --python .\.venv\Scripts\python.exe -e ".[dev]"
.\.venv\Scripts\python.exe -m app.main --check   # ortam doğrulaması (UI açmaz)
.\.venv\Scripts\python.exe -m app.main           # HUD (Faz 0: legacy köprü)
.\.venv\Scripts\python.exe -m pytest             # testler
```

## Yapı
```
legacy/          salt-okunur referans (jarvis-windows, v2-windows, v3-mac)
app/             yeni ULTRON kodu (Faz 1'den itibaren çekirdek buraya)
tests/           birim + güvenlik testleri
docs/            mimari/güvenlik/runbook (Faz 9'da tamamlanır)
```
