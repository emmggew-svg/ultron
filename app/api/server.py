"""ULTRON FastAPI Bridge — mevcut çekirdeği HTTP/WebSocket'e açar."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Mevcut ULTRON çekirdeğini import et
import sys
sys.path.insert(0, "C:\\ultron")

from app.tools.loader import load_all
from app.tools.registry import get_registry
from app.core.events import BUS, EventBus
from app.voice.audio_io import AudioIO
from app.voice.live_session import LiveSessionManager
from app.security.killswitch import KILLSWITCH


# --- Pydantic Modeller ---
class ChatRequest(BaseModel):
    message: str
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict] = []


class ToolCallRequest(BaseModel):
    tool: str
    args: dict


class ToolCallResponse(BaseModel):
    ok: bool
    message: str
    data: dict | None = None
    error: str | None = None


class StatusResponse(BaseModel):
    state: str
    uptime_seconds: float
    tools: int
    kill_switch_active: bool


# --- Uygulama Yaşam Döngüsü ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıç
    app.state.registry = load_all()
    app.state.audio = AudioIO(hardware=False)  # Web'de donanım yok
    app.state.bus = BUS
    app.state.session_manager = LiveSessionManager(
        system_text="Sen ULTRON'sun. Kısa, net Türkçe cevap ver.",
        audio=app.state.audio,
        registry=app.state.registry,
        bus=app.state.bus,
        data_dir="C:\\ultron\\app\\data",
    )
    app.state.start_time = datetime.now()
    
    # Olay dinleyicileri
    app.state.event_queue: asyncio.Queue = asyncio.Queue()
    BUS.on("state_changed", lambda e, p: app.state.event_queue.put_nowait({"type": "state", "data": p}))
    BUS.on("tool_requested", lambda e, p: app.state.event_queue.put_nowait({"type": "tool_requested", "data": p}))
    BUS.on("tool_completed", lambda e, p: app.state.event_queue.put_nowait({"type": "tool_completed", "data": p}))
    BUS.on("assistant_utterance", lambda e, p: app.state.event_queue.put_nowait({"type": "utterance", "data": p}))
    BUS.on("user_utterance", lambda e, p: app.state.event_queue.put_nowait({"type": "user_utterance", "data": p}))
    BUS.on("assistant_interrupted", lambda e, p: app.state.event_queue.put_nowait({"type": "interrupted", "data": p}))
    BUS.on("error", lambda e, p: app.state.event_queue.put_nowait({"type": "error", "data": p}))
    
    # Kill switch callback
    KILLSWITCH.on_trip(lambda r: app.state.event_queue.put_nowait({
        "type": "killswitch", "data": {"reason": r}
    }))
    
    yield
    
    # Kapanış
    app.state.session_manager.stop()
    app.state.audio.close()


app = FastAPI(title="ULTRON API", version="0.3.1", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REST Endpoints ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ultron-api", "version": "0.3.1"}


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    return StatusResponse(
        state="ready",
        uptime_seconds=(datetime.now() - app.state.start_time).total_seconds(),
        tools=len(app.state.registry.names()),
        kill_switch_active=KILLSWITCH.tripped,
    )


@app.get("/api/tools")
async def list_tools():
    reg = app.state.registry
    return {"tools": [
        {"name": t.name, "description": t.description, "risk": t.risk.value, "requires_confirmation": t.requires_confirmation}
        for t in [reg.get(n) for n in reg.names()]
    ]}


@app.post("/api/tools/call", response_model=ToolCallResponse)
async def call_tool(req: ToolCallRequest):
    reg = app.state.registry
    if req.tool not in reg.names():
        raise HTTPException(404, f"Tool not found: {req.tool}")
    result = await reg.call(req.tool, req.args)
    return ToolCallResponse(ok=result.ok, message=result.message, data=result.data, error=result.error)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Basit: tool registry'den LLM çağrısı simülasyonu
    # Gerçek implementasyonda LiveSessionManager ile sesli sohbet
    reg = app.state.registry
    
    # Basit: eğer mesaj "saat" içeriyorsa sys_info çağır
    tool_calls = []
    response_text = "Anlaşıldı."
    
    if "saat" in req.message.lower() or "saat kaç" in req.message.lower():
        result = await reg.call("sys_info", {"query": "time"})
        response_text = result.message
        tool_calls.append({"tool": "sys_info", "args": {"query": "time"}, "result": result.message})
    elif "hava" in req.message.lower():
        result = await reg.call("get_weather", {"location": ""})
        response_text = result.message
        tool_calls.append({"tool": "get_weather", "args": {"location": ""}, "result": result.message})
    
    return ChatResponse(response=response_text, tool_calls=tool_calls)


# --- WebSocket (Real-time events + audio streaming) ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    queue = asyncio.Queue()
    
    # Backend event'lerini forward et
    async def forward_events():
        while True:
            try:
                event = await app.state.event_queue.get()
                await ws.send_json(event)
            except Exception:
                break
    
    forward_task = asyncio.create_task(forward_events())
    
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})
            elif msg.get("type") == "audio_chunk":
                # Audio chunk'ını session manager'a forward et
                pass
            elif msg.get("type") == "chat":
                # Chat message
                response = await chat(ChatRequest(message=msg["message"]))
                await ws.send_json({"type": "chat_response", "data": response.model_dump()})
            elif msg.get("type") == "tool_call":
                result = await call_tool(ToolCallRequest(**msg["data"]))
                await ws.send_json({"type": "tool_result", "data": result.model_dump()})
            elif msg.get("type") == "kill_switch":
                KILLSWITCH.trigger(msg.get("reason", "manual"))
                await ws.send_json({"type": "kill_switch_activated"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await ws.send_json({"type": "error", "data": str(e)})
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)