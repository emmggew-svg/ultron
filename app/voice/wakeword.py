"""Uyandırma katmanı — spec §6.1. B-18 gereği mikrofonu AÇMAZ; AudioIO'ya abone olur.

Durumlar: IDLE (yalnızca yerel algılama) → ACTIVE (Live'a akış) → IDLE
(sessizlik zaman aşımı veya "teşekkürler Ultron").
- Varsayılan backend: çift-alkış (legacy'den port, eşikler aynı).
- "Ultron" kelimesi için Porcupine/openWakeWord backend'i S-03'e bağlıdır;
  anahtar/model yokken ClapBackend kullanılır (güvenli varsayılan).
"""
from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any

from app.voice.live_config import SILENCE_TIMEOUT_SECONDS

CLAP_THRESHOLD = 1800       # Int16 RMS eşiği (legacy ile aynı)
CLAP_MIN_GAP = 0.12         # Aynı alkışın karelere yayılmasını önler
CLAP_WINDOW = 2.0           # İki alkış bu süre içinde olmalı


def rms_level(data: bytes) -> float:
    count = len(data) // 2
    if count == 0:
        return 0.0
    shorts = struct.unpack(f"{count}h", data)
    return math.sqrt(sum(s * s for s in shorts) / count)


class ClapBackend:
    """Çift-alkış algılayıcı (yedek yöntem)."""

    def __init__(self, *, threshold: float = CLAP_THRESHOLD,
                 window: float = CLAP_WINDOW) -> None:
        self.threshold = threshold
        self.window = window
        self._claps: list[float] = []

    def process_frame(self, frame: bytes, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        self._claps = [t for t in self._claps if now - t < self.window]
        if rms_level(frame) <= self.threshold:
            return False
        if self._claps and (now - self._claps[-1]) < CLAP_MIN_GAP:
            return False
        self._claps.append(now)
        if len(self._claps) >= 2:
            self._claps = []
            return True
        return False


@dataclass
class WakeState:
    active: bool = False
    last_activity: float = field(default_factory=time.monotonic)


class WakeWordDetector:
    """IDLE/ACTIVE durum makinesi. Herhangi bir backend ile çalışır."""

    def __init__(self, backend: Any = None,
                 silence_timeout: float = SILENCE_TIMEOUT_SECONDS) -> None:
        self.backend = backend or ClapBackend()
        self.silence_timeout = silence_timeout
        self.state = WakeState()

    def on_frame(self, frame: bytes) -> bool:
        """True dönerse yeni uyanma oldu."""
        if self.backend.process_frame(frame):
            self.state.active = True
            self.state.last_activity = time.monotonic()
            return True
        return False

    def mark_activity(self) -> None:
        self.state.last_activity = time.monotonic()

    def check_idle_timeout(self, now: float | None = None) -> bool:
        """Zaman aşımı dolduysa IDLE'a döndürür, True döner."""
        now = time.monotonic() if now is None else now
        if self.state.active and (now - self.state.last_activity) > self.silence_timeout:
            self.state.active = False
            return True
        return False

    def deactivate(self, reason: str = "") -> None:  # reason: log amaçlı
        self.state.active = False
