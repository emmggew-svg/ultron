"""ULTRON Tool Registry — spec §3.3 (B-19'un çözümü).

Her araç TEK dosyada tanımlanır: şema + fonksiyon + risk seviyesi.
Registry, Gemini `function_declarations` şemasını otomatik üretir (elle JSON yok).

Kurallar:
- Araç dönüşü STANDART: ToolResult. Hata tespiti `ok` alanıyla yapılır (B-15);
  sonuç metninde "hata/error" geçmesi tek başına hata sayılmaz.
- Tanımsız araç çağrısı REDDEDİLİR (default-deny, spec §5.2).
- Senkron fonksiyonlar desteklenir; çalıştırma yolu thread-pool kullanır (B-09).
- Her çağrı denetlenebilir: opsiyonel `recorder` callback
  (tool, args, risk, decision, ok, süre_ms) alır — audit modülü Faz 1'de bağlanır.
"""
from __future__ import annotations

import asyncio
import dataclasses
import functools
import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Risk(str, Enum):
    SAFE = "SAFE"           # salt okuma, yan etkisiz
    LOW = "LOW"             # uygulama açma, URL açma, arama
    MEDIUM = "MEDIUM"       # dosya yazma (izinli kök), taslak, takvim/görev ekleme
    HIGH = "HIGH"           # gönderme, silme/taşıma, kabuk, otomasyon — HER SEFERİNDE ONAY
    CRITICAL = "CRITICAL"   # varsayılan KAPALI — ayar + her seferinde onay


# Spec §3.3 param kısayolu: {"ad": ("tip", "açıklama", zorunlu_mu)}
ParamSpec = tuple[str, str, bool]

_GEMINI_TYPES = {
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
}


@dataclass
class ToolResult:
    """Standart araç dönüşü (spec §8.2)."""

    ok: bool
    message: str                            # kullanıcıya/modele kısa özet
    data: dict[str, Any] | None = None
    error: str | None = None
    untrusted_content: bool = False         # True ise §5.6 kuralları uygulanır
    undo: dict[str, Any] | None = None      # geri alma bilgisi


@dataclass
class ToolDef:
    name: str
    description: str
    risk: Risk
    requires_confirmation: bool
    params: Mapping[str, ParamSpec]
    timeout: float
    func: Callable[..., Any]
    is_async: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_async = inspect.iscoroutinefunction(self.func)

    def gemini_declaration(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        for pname, (ptype, pdesc, preq) in self.params.items():
            if ptype not in _GEMINI_TYPES:
                raise ValueError(f"[{self.name}] bilinmeyen param tipi: {ptype}")
            properties[pname] = {"type": _GEMINI_TYPES[ptype], "description": pdesc}
            if preq:
                required.append(pname)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "OBJECT",
                "properties": properties,
                "required": required,
            },
        }


# (tool, args, risk, decision, ok, süre_ms) — audit bağlanana kadar None
AuditRecorder = Callable[[str, dict[str, Any], Risk, str, bool, int], None]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}
        self.recorder: AuditRecorder | None = None

    def register(self, tooldef: ToolDef) -> ToolDef:
        if tooldef.name in self._tools:
            raise ValueError(f"araç zaten kayıtlı: {tooldef.name}")
        self._tools[tooldef.name] = tooldef
        return tooldef

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def gemini_declarations(self) -> list[dict[str, Any]]:
        return [t.gemini_declaration() for t in self._tools.values()]

    async def call(self, name: str, args: Mapping[str, Any] | None = None) -> ToolResult:
        import time

        args = dict(args or {})
        started = time.monotonic()
        tooldef = self._tools.get(name)
        if tooldef is None:
            # default-deny: tanımsız araç = ret
            return ToolResult(ok=False, message=f"Bilinmeyen araç reddedildi: {name}",
                              error=f"unknown_tool:{name}")

        # Faz 1: requires_confirmation True ise karar ON MODÜLE sorulur;
        # confirm modülü bağlanana kadar HIGH/CRITICAL otomatik RED (güvenli varsayılan).
        decision = "auto"
        if tooldef.requires_confirmation:
            decision = "denied"
            result = ToolResult(
                ok=False,
                message=f"Onay gerekli: {name} ({tooldef.risk.value}). Onay modülü bağlı değil.",
                error="confirmation_required",
            )
            self._record(name, args, tooldef.risk, decision, False, started)
            return result

        try:
            if tooldef.is_async:
                raw = await asyncio.wait_for(
                    tooldef.func(**args), timeout=tooldef.timeout)
            else:
                raw = await asyncio.wait_for(
                    asyncio.to_thread(tooldef.func, **args), timeout=tooldef.timeout)
        except asyncio.TimeoutError:
            result = ToolResult(ok=False, message=f"{name} zaman aşımına uğradı.",
                                error=f"timeout:{tooldef.timeout}s")
            self._record(name, args, tooldef.risk, decision, False, started)
            return result
        except TypeError as exc:
            result = ToolResult(ok=False, message=f"{name}: argüman hatası.",
                                error=f"bad_args:{exc}")
            self._record(name, args, tooldef.risk, decision, False, started)
            return result
        except Exception as exc:  # araç içi beklenmedik hata — sistem ayakta kalır (ilke §1.3.5)
            result = ToolResult(ok=False, message=f"{name} çalışırken hata oluştu.",
                                error=f"{type(exc).__name__}: {exc}")
            self._record(name, args, tooldef.risk, decision, False, started)
            return result

        result = self._normalize(name, raw)
        self._record(name, args, tooldef.risk, decision, result.ok, started)
        return result

    @staticmethod
    def _normalize(name: str, raw: Any) -> ToolResult:
        # B-15: karar SADECE ok alanına bakılarak verilir.
        if isinstance(raw, ToolResult):
            return raw
        if isinstance(raw, bool):
            return ToolResult(ok=raw, message=f"{name}: {'tamam' if raw else 'başarısız'}")
        if raw is None:
            return ToolResult(ok=True, message=f"{name}: tamam.")
        return ToolResult(ok=True, message=str(raw))

    def _record(self, name: str, args: dict[str, Any], risk: Risk,
                decision: str, ok: bool, started: float) -> None:
        if self.recorder is None:
            return
        import time

        try:
            self.recorder(name, args, risk, decision, ok, int((time.monotonic() - started) * 1000))
        except Exception:
            pass  # kayıt hatası aracı durdurmaz


REGISTRY = ToolRegistry()


def tool(*, name: str, description: str, risk: Risk = Risk.LOW,
         requires_confirmation: bool = False,
         params: Mapping[str, ParamSpec] | None = None,
         timeout: float = 30.0):
    """Araç dekoratörü (spec §3.3). Örnek:
    @tool(name="saat", description="...", risk=Risk.SAFE, params={})
    async def saat() -> ToolResult: ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tooldef = ToolDef(
            name=name,
            description=description,
            risk=risk,
            requires_confirmation=requires_confirmation or risk in (Risk.HIGH, Risk.CRITICAL),
            params=params or {},
            timeout=timeout,
            func=func,
        )
        REGISTRY.register(tooldef)

        @functools.wraps(func)
        def wrapper(*a: Any, **k: Any) -> Any:
            return func(*a, **k)

        wrapper.__ultron_tool__ = tooldef  # type: ignore[attr-defined]
        return wrapper

    return decorator


def get_registry() -> ToolRegistry:
    return REGISTRY


__all__ = [
    "Risk", "ParamSpec", "ToolResult", "ToolDef", "ToolRegistry",
    "REGISTRY", "tool", "get_registry",
]
