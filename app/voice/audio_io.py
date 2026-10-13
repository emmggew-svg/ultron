"""Tek ses sahibi — spec §6.1, B-18'in çözümü.

Mikrofonu SADECE AudioIO açar; wake-word, Live akışı ve yedek dinleyiciler
aynı kareleri abone modeliyle alır (iki PyAudio örneği YOK).
Hoparlör kuyruğu kesilebilir: barge-in anında flush() çağrılır (B-08).
"""
from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Callable

try:
    import pyaudio
    _HAS_PYAUDIO = True
except Exception:
    pyaudio = None  # type: ignore[assignment]
    _HAS_PYAUDIO = False

from app.voice.live_config import CHANNELS, CHUNK_SIZE, RECV_SAMPLE_RATE, SEND_SAMPLE_RATE

FrameCallback = Callable[[bytes], None]


class AudioIO:
    """Mikrofon + hoparlörün tek sahibi. Testlerde donanımsız da kurulabilir."""

    def __init__(self, *, hardware: bool = True) -> None:
        self._hardware = hardware and _HAS_PYAUDIO
        self._pa = None
        self._in_stream = None
        self._out_stream = None
        self._subscribers: list[FrameCallback] = []
        self._sub_lock = threading.Lock()
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None
        self.out_queue: asyncio.Queue = asyncio.Queue()
        self._play_task: asyncio.Task | None = None

    # -- giriş --
    def subscribe(self, callback: FrameCallback) -> None:
        with self._sub_lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: FrameCallback) -> None:
        with self._sub_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def push_frame(self, frame: bytes) -> None:
        """Donanımsız testler / enjeksiyon için karekök giriş."""
        with self._sub_lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(frame)
            except Exception:
                pass

    def start_input(self) -> None:
        if not self._hardware:
            return
        self._pa = pyaudio.PyAudio()
        self._in_stream = self._pa.open(format=pyaudio.paInt16, channels=CHANNELS,
                                        rate=SEND_SAMPLE_RATE, input=True,
                                        frames_per_buffer=CHUNK_SIZE)
        self._stop.clear()
        self._reader = threading.Thread(target=self._read_loop, daemon=True, name="UltronMic")
        self._reader.start()

    def _read_loop(self) -> None:
        assert self._in_stream is not None
        while not self._stop.is_set():
            try:
                data = self._in_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            except Exception:
                break
            self.push_frame(data)

    def stop_input(self) -> None:
        self._stop.set()
        try:
            if self._in_stream is not None:
                self._in_stream.stop_stream()
                self._in_stream.close()
        except Exception:
            pass
        try:
            if self._pa is not None:
                self._pa.terminate()
        except Exception:
            pass
        self._in_stream, self._pa = None, None

    # -- çıkış --
    def flush_output(self) -> int:
        """Barge-in: çalınmamış kuyruğu boşalt. Atılan chunk sayısını döner."""
        dropped = 0
        try:
            while True:
                self.out_queue.get_nowait()
                dropped += 1
        except (asyncio.QueueEmpty, Exception):
            pass
        return dropped

    async def play_loop(self) -> None:
        """Hoparlör döngüsü (donanım yoksa kareleri yutar)."""
        out = None
        if self._hardware:
            if self._pa is None:
                self._pa = pyaudio.PyAudio()
            out = self._pa.open(format=pyaudio.paInt16, channels=CHANNELS,
                                rate=RECV_SAMPLE_RATE, output=True,
                                frames_per_buffer=CHUNK_SIZE)
        try:
            while True:
                chunk = await self.out_queue.get()
                if chunk is None:  # turn sonu sentinel'i
                    continue
                if out is not None:
                    try:
                        out.write(chunk)
                    except Exception:
                        pass
        finally:
            try:
                if out is not None:
                    out.stop_stream()
                    out.close()
            except Exception:
                pass
