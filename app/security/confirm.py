"""Onay akışı çekirdeği — spec §5.3.

Kurallar:
- Onay zaman aşımı → otomatik RED (varsayılan 60 sn).
- Kill switch aktifken → otomatik RED.
- Onaylayıcı (approver) enjekte edilir; yoksa RED (güvenli varsayılan).
  Faz 9'da Tk onay penceresi bağlanır; çekirdek UI'dan bağımsızdır ve test edilir.
- "Hep izin ver" yalnızca MEDIUM için sunulabilir — bu modül kararı üretmez,
  sadece tek seferlik onay/ret döndürür; kalıcı izin politikası Faz 7+ işidir.
"""
from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.security.killswitch import KILLSWITCH

DEFAULT_TIMEOUT_SECONDS = 60.0


@dataclass
class ApprovalRequest:
    tool: str
    summary: str                       # eylem özeti ("X dosyasını Geri Dönüşüm Kutusu'na taşı")
    target: str = ""                   # hedef (kime / hangi dosya)
    content_preview: str = ""          # tam içerik/diff önizlemesi
    risk: str = "MEDIUM"
    undo_info: str = ""                # geri alma yolu ("Geri Dönüşüm Kutusu'ndan geri alınabilir")


@dataclass
class ApprovalDecision:
    approved: bool
    decided_by: str                    # "user" | "timeout" | "killswitch" | "no-approver" | "error"
    latency_ms: int = 0


Approver = Callable[[ApprovalRequest], Any]  # bool veya awaitable[bool] döndürür


async def request_approval(request: ApprovalRequest,
                           approver: Approver | None = None,
                           timeout: float = DEFAULT_TIMEOUT_SECONDS) -> ApprovalDecision:
    started = time.monotonic()

    def elapsed() -> int:
        return int((time.monotonic() - started) * 1000)

    if KILLSWITCH.tripped:
        return ApprovalDecision(approved=False, decided_by="killswitch", latency_ms=elapsed())
    if approver is None:
        return ApprovalDecision(approved=False, decided_by="no-approver", latency_ms=elapsed())

    try:
        result = approver(request)
        if inspect.isawaitable(result):
            approved = bool(await asyncio.wait_for(result, timeout=timeout))
        else:
            approved = bool(result)
        return ApprovalDecision(approved=approved, decided_by="user", latency_ms=elapsed())
    except TimeoutError:
        return ApprovalDecision(approved=False, decided_by="timeout", latency_ms=elapsed())
    except Exception:
        return ApprovalDecision(approved=False, decided_by="error", latency_ms=elapsed())


def request_approval_sync(request: ApprovalRequest,
                          approver: Approver | None = None,
                          timeout: float = DEFAULT_TIMEOUT_SECONDS) -> ApprovalDecision:
    return asyncio.run(request_approval(request, approver, timeout))
