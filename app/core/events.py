"""Olay veriyolu — spec §8.3. UI, görevler ve ses katmanı buradan haberleşir."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

Handler = Callable[[str, Any], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def on(self, event: str, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Handler) -> None:
        if handler in self._handlers.get(event, []):
            self._handlers[event].remove(handler)

    def emit(self, event: str, payload: Any = None) -> None:
        for handler in list(self._handlers.get(event, [])):
            try:
                handler(event, payload)
            except Exception:
                pass


BUS = EventBus()
