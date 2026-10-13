"""Ses katmanı testleri — Faz 2. Donanım GEREKTİRMEZ (sahte oturum + sentetik kareler)."""
from __future__ import annotations

import asyncio
import struct
import types as pytypes

from app.core.events import EventBus
from app.tools.loader import load_all
from app.tools.registry import ToolRegistry
from app.voice import live_config as cfg
from app.voice.audio_io import AudioIO
from app.voice.live_session import LiveSessionManager, backoff_seconds
from app.voice.wakeword import ClapBackend, WakeWordDetector, rms_level

load_all()


def _ns(**kwargs):
    return pytypes.SimpleNamespace(**kwargs)


def _loud_frame(value: int = 12000, n: int = 512) -> bytes:
    return struct.pack(f"{n}h", *([value] * n))


def _silent_frame(n: int = 512) -> bytes:
    return struct.pack(f"{n}h", *([0] * n))


# -- sabit mühürleri (kullanıcı şartı: ses birebir Jarvis) --
def test_voice_pinned_charon():
    assert cfg.VOICE_NAME == "Charon"
    assert cfg.VOICE_OPTIONS == ("Charon",)


def test_live_model_current():
    assert cfg.LIVE_MODEL == "gemini-3.8-live"


def test_audio_constants_match_live_spec():
    assert (cfg.SEND_SAMPLE_RATE, cfg.RECV_SAMPLE_RATE, cfg.CHANNELS) == (16000, 24000, 1)


# -- AudioIO --
def test_single_owner_fanout():
    audio = AudioIO(hardware=False)
    got_a, got_b = [], []
    audio.subscribe(got_a.append)
    audio.subscribe(got_b.append)
    audio.push_frame(b"\x01\x02")
    assert got_a == got_b == [b"\x01\x02"]
    audio.unsubscribe(got_a.append)
    audio.push_frame(b"\x03")
    assert got_a == [b"\x01\x02"] and got_b == [b"\x01\x02", b"\x03"]


def test_flush_output():
    audio = AudioIO(hardware=False)

    async def fill():
        for i in range(3):
            audio.out_queue.put_nowait(bytes([i]))

    asyncio.run(fill())
    assert audio.flush_output() == 3
    assert audio.flush_output() == 0


# -- wake word --
def test_rms_silence_vs_clap():
    assert rms_level(_silent_frame()) == 0.0
    assert rms_level(_loud_frame()) > 1800


def test_double_clap_wakes():
    backend = ClapBackend()
    assert backend.process_frame(_silent_frame(), now=100.0) is False
    assert backend.process_frame(_loud_frame(), now=100.1) is False  # ilk alkış
    assert backend.process_frame(_loud_frame(), now=100.5) is True   # ikinci → uyanma


def test_clap_window_expiry():
    backend = ClapBackend()
    assert backend.process_frame(_loud_frame(), now=200.0) is False
    assert backend.process_frame(_loud_frame(), now=203.5) is False  # pencere dışı


def test_idle_timeout():
    det = WakeWordDetector(silence_timeout=20.0)
    det.state.active = True
    det.state.last_activity = 500.0
    assert det.check_idle_timeout(now=510.0) is False
    assert det.check_idle_timeout(now=521.0) is True
    assert det.state.active is False


# -- LiveSessionManager --
class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.tool_responses = None

    async def receive(self):
        for response in self.responses:
            yield response

    async def send_tool_response(self, function_responses):
        self.tool_responses = function_responses

    async def send_realtime_input(self, **kwargs):
        pass


def _mgr(tmp_path, **kw):
    bus = EventBus()
    events = []
    for name in ("tool_completed", "assistant_interrupted", "user_utterance",
                 "assistant_utterance", "turn_complete", "state_changed"):
        bus.on(name, lambda e, p, _n=name: events.append((_n, p)))
    return LiveSessionManager(system_text="test", audio=AudioIO(hardware=False),
                              registry=ToolRegistry(), data_dir=tmp_path,
                              bus=bus, **kw), events


def test_handle_roundtrip(tmp_path):
    mgr, _ = _mgr(tmp_path)
    assert mgr.load_handle() is None
    mgr.save_handle("tutamac-123")
    assert LiveSessionManager(system_text="t", data_dir=tmp_path).load_handle() == "tutamac-123"


def test_resumption_update_saves_handle(tmp_path):
    mgr, _ = _mgr(tmp_path)
    session = FakeSession([_ns(data=None, server_content=None,
                               session_resumption_update=_ns(new_handle="H-1"),
                               go_away=None, tool_call=None)])
    asyncio.run(mgr._receive_loop(session))
    assert mgr.load_handle() == "H-1"


def test_tool_call_runs_in_background(tmp_path):
    from app.tools.registry import get_registry

    bus = EventBus()
    events = []
    bus.on("tool_completed", lambda e, p: events.append((e, p)))
    mgr = LiveSessionManager(system_text="test", audio=AudioIO(hardware=False),
                             registry=get_registry(), data_dir=tmp_path, bus=bus)
    fc = _ns(name="sys_info", args={"query": "time"})
    session = FakeSession([_ns(data=None, server_content=None,
                               session_resumption_update=None,
                               go_away=None, tool_call=_ns(function_calls=[fc]))])
    asyncio.run(mgr._receive_loop(session))
    assert session.tool_responses and session.tool_responses[0]["name"] == "sys_info"
    assert any(e[0] == "tool_completed" and e[1]["ok"] for e in events)


def test_interrupted_flushes_audio(tmp_path):
    mgr, events = _mgr(tmp_path)

    async def fill():
        mgr.audio.out_queue.put_nowait(b"1")
        mgr.audio.out_queue.put_nowait(b"2")

    asyncio.run(fill())
    session = FakeSession([_ns(data=None,
                               server_content=_ns(interrupted=True, turn_complete=False,
                                                  output_transcription=None,
                                                  input_transcription=None),
                               session_resumption_update=None,
                               go_away=None, tool_call=None)])
    asyncio.run(mgr._receive_loop(session))
    assert mgr.audio.out_queue.empty()
    assert any(e[0] == "assistant_interrupted" and e[1]["dropped_chunks"] == 2
               for e in events)


def test_goaway_returns(tmp_path):
    mgr, _ = _mgr(tmp_path)
    session = FakeSession([_ns(data=None, server_content=None,
                               session_resumption_update=None,
                               go_away=_ns(time_left=5), tool_call=None)])
    asyncio.run(mgr._receive_loop(session))  # dönmezse test asılır


def test_backoff_caps():
    assert [backoff_seconds(i) for i in range(8)] == [1, 2, 4, 8, 16, 32, 60, 60]


def test_build_config_pins_voice_and_model(tmp_path):
    mgr, _ = _mgr(tmp_path)
    config = mgr.build_config()
    assert config.speech_config.voice_config.prebuilt_voice_config.voice_name == "Charon"
    assert config.session_resumption is not None
    assert config.context_window_compression is not None
