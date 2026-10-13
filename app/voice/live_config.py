"""Live bağlantı sabitleri — TEK NOKTA (S-01 çözümü).

- Model: güncel dokümandan doğrulandı (2026-10-13, ai.google.dev/gemini-api/docs/models).
  Legacy adı `gemini-2.5-flash-native-audio-latest` katalogda YOK; güncel varsayılan
  Live modeli `gemini-3.8-live`. Değişirse SADECE burası değişir.
- Ses: **Charon** — Jarvis'in birebir sesi (3 pakette de varsayılan; kullanıcı isteğiyle
  sabitlendi). DEĞİŞTİRİLMEZ; ayar panelinde ses seçimi Faz 9'a kadar kapalıdır.
"""
from __future__ import annotations

# -- model + ses (SABİT) --
LIVE_MODEL = "gemini-3.8-live"
VOICE_NAME = "Charon"  # Jarvis'in sesi — birebir aynı
VOICE_OPTIONS = ("Charon",)  # Faz 9'a kadar tek seçenek

# -- ses donanımı (Live API teknik şartnamesi: 16-bit PCM LE) --
SEND_SAMPLE_RATE = 16000  # mikrofon → model
RECV_SAMPLE_RATE = 24000  # model → hoparlör
CHANNELS = 1
CHUNK_SIZE = 1024

# -- oturum dayanıklılığı (B-07) --
SESSION_HANDLE_FILE = "session_handle.json"  # app/data altında tutulur
RECONNECT_BASE_SECONDS = 1.0
RECONNECT_MAX_SECONDS = 60.0
SILENCE_TIMEOUT_SECONDS = 20.0  # ACTIVE → IDLE dönüşü

# -- görev sınırları (spec §3.4) --
MAX_TOOL_TASKS = 8  # aynı anda arka planda koşan araç çağrısı üst sınırı
