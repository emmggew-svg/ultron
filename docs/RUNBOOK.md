# RUNBOOK — ULTRON elle test rehberi (Faz 0)

## Faz 0 kabul testleri (elle)
1. `python -m app.main --check` → `CHECK OK` (mikrofon/UI gerekmez).
2. `python -m pytest` → tüm testler yeşil.
3. `python -m app.main` → legacy HUD penceresi açılır, API-key ekranı gelir.
   Bağlantı testi API anahtarı gerektirir; anahtar yoksa bu adım "test edilemedi" sayılır.

## Test edilemeyenler (Faz 0)
- [ ] Gemini Live bağlantısı (API anahtarı + internet gerekir) — Faz 2'de.
- [ ] Mikrofon/çift-alkış (donanım + sesli ortam gerekir).

## Faz 2 kabul testleri (elle — API anahtarı + mikrofon gerekir)
1. 30+ dakikalık oturum: bağlam kaybı yok, kopmalarda aynı konuşmaya devam.
2. Barge-in: Ultron konuşurken araya girince ~300 ms içinde susuyor mu? (kronometreyle)
3. Wake word: 20 sessiz dakika + 10 TV/gürültü denemesi → yanlış-pozitif sayısını not et.
4. Yankı: hoparlör+mikrofon modunda kendi sesine takılıyor mu? Takılıyorsa KULAKLIK TAK
   (donanımsal AEC yok — kod değil fizik sınırı, system.md'de de yazar).
5. Kill: "Ultron dur" + Ctrl+Alt+Shift+K (Faz 6'da bağlanacak) tüm sesi kesiyor mu?
