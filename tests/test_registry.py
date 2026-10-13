"""Registry + ToolResult testleri (B-15/B-19 regresyonları dahil)."""
from __future__ import annotations

import asyncio

import pytest

from app.tools.registry import Risk, ToolRegistry, ToolResult, tool


def _fresh() -> ToolRegistry:
    return ToolRegistry()


def test_register_and_schema():
    reg = _fresh()

    @tool(name="t_selam", description="Selam verir.", risk=Risk.SAFE,
          params={"kime": ("string", "Kime selam", True)}, timeout=5)
    async def _f(kime: str) -> ToolResult:
        return ToolResult(ok=True, message=f"Selam {kime}")

    # dekoratör global REGISTRY'ye de yazdı; izole registry'e elle ekle
    reg.register(_f.__ultron_tool__)
    assert reg.names() == ["t_selam"]
    decl = reg.gemini_declarations()[0]
    assert decl["name"] == "t_selam"
    assert decl["parameters"]["properties"]["kime"]["type"] == "STRING"
    assert decl["parameters"]["required"] == ["kime"]


def test_duplicate_rejected():
    reg = _fresh()

    @tool(name="t_dup", description="x", risk=Risk.SAFE)
    async def _f() -> ToolResult:
        return ToolResult(ok=True, message="ok")

    reg.register(_f.__ultron_tool__)
    with pytest.raises(ValueError):
        reg.register(_f.__ultron_tool__)


def test_unknown_tool_denied():
    reg = _fresh()
    res = asyncio.run(reg.call("olmayan_arac", {}))
    assert res.ok is False and res.error.startswith("unknown_tool")


def test_ok_field_decides_not_text():
    """B-15 regresyonu: ok=True + 'gerekli' kelimesi = BAŞARI sayılmalı."""
    reg = _fresh()

    @tool(name="t_metin", description="x", risk=Risk.SAFE)
    async def _f() -> ToolResult:
        return ToolResult(ok=True, message="Kurulum için bilgi gerekli. Her şey hazır.")

    reg.register(_f.__ultron_tool__)
    res = asyncio.run(reg.call("t_metin", {}))
    assert res.ok is True


def test_error_result_is_error():
    reg = _fresh()

    @tool(name="t_hata", description="x", risk=Risk.SAFE)
    async def _f() -> ToolResult:
        return ToolResult(ok=False, message="bir şeyler ters gitti", error="ornek")

    reg.register(_f.__ultron_tool__)
    res = asyncio.run(reg.call("t_hata", {}))
    assert res.ok is False


def test_requires_confirmation_defaults_denied():
    """HIGH araç, confirm modülü yokken OTOMATİK RED (güvenli varsayılan)."""
    reg = _fresh()

    @tool(name="t_riskli", description="x", risk=Risk.HIGH)
    async def _f() -> ToolResult:
        return ToolResult(ok=True, message="asla")

    reg.register(_f.__ultron_tool__)
    res = asyncio.run(reg.call("t_riskli", {}))
    assert res.ok is False and res.error == "confirmation_required"


def test_sync_func_runs():
    reg = _fresh()

    @tool(name="t_sync", description="x", risk=Risk.SAFE)
    def _f() -> str:
        return "senkron tamam"

    reg.register(_f.__ultron_tool__)
    res = asyncio.run(reg.call("t_sync", {}))
    assert res.ok is True and "senkron" in res.message


def test_timeout():
    reg = _fresh()

    @tool(name="t_yavas", description="x", risk=Risk.SAFE, timeout=0.05)
    async def _f() -> ToolResult:
        await asyncio.sleep(5)
        return ToolResult(ok=True, message="asla")

    reg.register(_f.__ultron_tool__)
    res = asyncio.run(reg.call("t_yavas", {}))
    assert res.ok is False and res.error.startswith("timeout")


def test_recorder_called():
    reg = _fresh()
    seen: list = []
    reg.recorder = lambda *a: seen.append(a)

    @tool(name="t_kayit", description="x", risk=Risk.LOW)
    async def _f() -> ToolResult:
        return ToolResult(ok=True, message="ok")

    reg.register(_f.__ultron_tool__)
    asyncio.run(reg.call("t_kayit", {"a": 1}))
    assert len(seen) == 1 and seen[0][0] == "t_kayit" and seen[0][3] == "auto"
