# RUNBOOK — ULTRON elle test rehberi (Faz 0)

## Faz 0 kabul testleri (elle)
1. `python -m app.main --check` → `CHECK OK` (mikrofon/UI gerekmez).
2. `python -m pytest` → tüm testler yeşil.
3. `python -m app.main` → legacy HUD penceresi açılır, API-key ekranı gelir.
   Bağlantı testi API anahtarı gerektirir; anahtar yoksa bu adım "test edilemedi" sayılır.

## Test edilemeyenler (Faz 0)
- [ ] Gemini Live bağlantısı (API anahtarı + internet gerekir) — Faz 2'de.
- [ ] Mikrofon/çift-alkış (donanım + sesli ortam gerekir).
