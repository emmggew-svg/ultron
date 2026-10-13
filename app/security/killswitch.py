"""Kill switch — spec §5.5. Global durdurma: görevler, otomasyon, mikrofon, onaylar.

Kullanım: KILLSWITCH.trigger("kullanıcı durdurdu") → tüm bekleyen işler AbortError alır,
confirm bekleyenler reddedilir. reset() ile normale dönülür.
"""
from __future__ import annotations

import threading


class KillSwitchTripped(Exception):
    """Kill switch aktifken başlatılmak istenen işin aldığı hata."""


class KillSwitch:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tripped = False
        self._reason = ""
        self._listeners: list = []

    def trigger(self, reason: str = "kullanıcı durdurdu") -> None:
        with self._lock:
            self._tripped = True
            self._reason = reason
        for fn in list(self._listeners):
            try:
                fn(reason)
            except Exception:
                pass

    def reset(self) -> None:
        with self._lock:
            self._tripped = False
            self._reason = ""

    @property
    def tripped(self) -> bool:
        with self._lock:
            return self._tripped

    @property
    def reason(self) -> str:
        with self._lock:
            return self._reason

    def check(self) -> None:
        """Uzun işler döngü başlarında bunu çağırır; aktifse AbortError yükseltir."""
        if self.tripped:
            raise KillSwitchTripped(self.reason or "kill switch aktif")

    def on_trip(self, fn) -> None:
        self._listeners.append(fn)


KILLSWITCH = KillSwitch()
