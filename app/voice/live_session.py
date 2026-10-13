"""Live oturum yöneticisi — spec §6.1, B-07/B-08/B-09 çözümleri.

- B-07: session_resumption tutamacı saklanır, kopuşta aynı tutamaçla devam;
  sliding-window compression açık; GoAway'de kesintisiz yeniden bağlanma;
  üstel geri çekilme (1,2,4… max 60 sn).
- B-08: mikrofon Ultron konuşurken KAPATILMAZ; `interrupted` gelince ses
  kuyruğu anında boşaltılır. NOT: hoparlör yankısı donanımsal AEC/kulaklık
  gerektirir; yoksa RUNBOOK'taki "kulaklık önerilir" uyarısı geçerlidir.
- B-09: araç çağrıları semaphore-sınırlı arka plan görevleridir; alım
  döngüsü bloke olmaz.
- Tüm SDK parametreleri live_config.py'den gelir; model/ses SABİTTİR.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.events import BUS, EventBus
from app.tools.registry import ToolRegistry, get_registry
from app.voice import live_config as cfg
from app.voice.audio_io import AudioIO


def backoff_seconds(attempt: int) -> float:
    delay = cfg.RECONNECT_BASE_SECONDS * (2 ** max(0, attempt))
    return min(delay, cfg.RECONNECT_MAX_SECONDS)


class LiveSessionManager:
    def __init__(self, *, system_text: str,
                 audio: AudioIO | None = None,
                 registry: ToolRegistry | None = None,
                 bus: EventBus | None = None,
                 data_dir: str | Path = "app/data",
                 connect_fn: Callable[..., Any] | None = None) -> None:
        self.system_text = system_text
        self.audio = audio or AudioIO(hardware=False)
        self.registry = registry or get_registry()
        self.bus: EventBus = bus or BUS
        self.data_dir = Path(data_dir)
        self._connect_fn = connect_fn
        self._stop = asyncio.Event()
        self._mic_sending = False

    # -- tutamaç kalıcılığı --
    @property
    def _handle_path(self) -> Path:
        return self.data_dir / cfg.SESSION_HANDLE_FILE

    def load_handle(self) -> str | None:
        try:
            if self._handle_path.exists():
                data = json.loads(self._handle_path.read_text(encoding="utf-8"))
                handle = data.get("handle")
                return handle or None
        except Exception:
            pass
        return None

    def save_handle(self, handle: str) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._handle_path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"handle": handle}), encoding="utf-8")
            tmp.replace(self._handle_path)
        except Exception:
            pass

    # -- config --
    def build_config(self):
        from google.genai import types

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=self.system_text,
            tools=[{"function_declarations": self.registry.gemini_declarations()}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=cfg.VOICE_NAME))),  # Charon — SABİT
            session_resumption=types.SessionResumptionConfig(handle=self.load_handle()),
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()),
        )

    # -- yaşam döngüsü --
    def stop(self) -> None:
        self._stop.set()

    async def run_forever(self, make_client: Callable[[], Any]) -> None:
        attempt = 0
        while not self._stop.is_set():
            try:
                await self._run_once(make_client)
                attempt = 0  # temiz kapanış sayılmaz; _run_once ancak kopuşta döner
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.bus.emit("error", {"where": "live_session", "error": str(exc)})
            if self._stop.is_set():
                break
            delay = backoff_seconds(attempt)
            self.bus.emit("state_changed", {"state": "RECONNECTING", "delay": delay})
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=delay)
            except TimeoutError:
                pass
            attempt += 1

    async def _run_once(self, make_client: Callable[[], Any]) -> None:
        client = make_client()
        config = self.build_config()
        connect = self._connect_fn or client.aio.live.connect
        async with connect(model=cfg.LIVE_MODEL, config=config) as session:
            self.bus.emit("state_changed", {"state": "LISTENING"})
            sender = asyncio.create_task(self._send_loop(session))
            receiver = asyncio.create_task(self._receive_loop(session))
            done, pending = await asyncio.wait(
                {sender, receiver}, return_when=asyncio.FIRST_EXCEPTION)
            for task in pending:
                task.cancel()
            for task in done:
                if not task.cancelled() and task.exception() is not None:
                    raise task.exception()

    async def _send_loop(self, session: Any) -> None:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_frame(frame: bytes) -> None:
            if self._mic_sending:
                loop.call_soon_threadsafe(queue.put_nowait, frame)

        self.audio.subscribe(on_frame)
        self._mic_sending = True  # B-08: konuşurken KAPANMAZ
        try:
            while not self._stop.is_set():
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                await session.send_realtime_input(
                    audio={"data": frame, "mime_type": "audio/pcm;rate=16000"})
        finally:
            self._mic_sending = False
            self.audio.unsubscribe(on_frame)

    async def _receive_loop(self, session: Any) -> None:
        sem = asyncio.Semaphore(cfg.MAX_TOOL_TASKS)

        async def run_tool(fc: Any) -> Any:
            async with sem:
                result = await self.registry.call(fc.name, dict(fc.args or {}))
                self.bus.emit("tool_completed",
                              {"tool": fc.name, "ok": result.ok, "message": result.message})
                return result

        async for response in session.receive():
            if self._stop.is_set():
                return
            data = getattr(response, "data", None)
            if data:
                try:
                    self.audio.out_queue.put_nowait(data)
                except Exception:
                    pass
            sc = getattr(response, "server_content", None)
            if sc is not None:
                if getattr(sc, "interrupted", False):
                    dropped = self.audio.flush_output()  # B-08: anında sus
                    self.bus.emit("assistant_interrupted", {"dropped_chunks": dropped})
                turn = getattr(sc, "turn_complete", False)
                if turn:
                    self.bus.emit("turn_complete", None)
                out_t = getattr(getattr(sc, "output_transcription", None), "text", "")
                if out_t:
                    self.bus.emit("assistant_utterance", {"text": out_t})
                in_t = getattr(getattr(sc, "input_transcription", None), "text", "")
                if in_t:
                    self.bus.emit("user_utterance", {"text": in_t})
            resume = getattr(response, "session_resumption_update", None)
            if resume is not None:
                handle = getattr(resume, "new_handle", "") or getattr(resume, "handle", "")
                if handle:
                    self.save_handle(handle)
            if getattr(response, "go_away", None) is not None:
                self.bus.emit("state_changed", {"state": "GOAWAY"})
                return  # _run_once döner → run_forever anında yeniden bağlanır
            tool_call = getattr(response, "tool_call", None)
            if tool_call is not None:
                calls = getattr(tool_call, "function_calls", []) or []
                self.bus.emit("tool_requested",
                              {"tools": [getattr(c, "name", "?") for c in calls]})
                results = await asyncio.gather(*(run_tool(fc) for fc in calls))
                await session.send_tool_response(
                    function_responses=[
                        {"name": fc.name, "response": {"result": r.message}}
                        for fc, r in zip(calls, results)
                    ])
