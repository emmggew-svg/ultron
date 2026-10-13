"""Onay çekirdeği testleri — spec §5.3 (timeout→red, killswitch→red)."""
from __future__ import annotations

import asyncio

from app.security.confirm import (
    ApprovalRequest,
    request_approval,
    request_approval_sync,
)
from app.security.killswitch import KILLSWITCH


def _req() -> ApprovalRequest:
    return ApprovalRequest(tool="mail_gonder", summary="X'e mail gönder",
                           target="a@b.com", risk="HIGH")


def test_no_approver_denied():
    d = request_approval_sync(_req(), None)
    assert d.approved is False and d.decided_by == "no-approver"


def test_user_approves():
    d = request_approval_sync(_req(), lambda r: True)
    assert d.approved is True and d.decided_by == "user"


def test_user_denies():
    d = request_approval_sync(_req(), lambda r: False)
    assert d.approved is False and d.decided_by == "user"


def test_timeout_denied():
    async def slow(_):
        await asyncio.sleep(5)
        return True

    d = asyncio.run(request_approval(_req(), slow, timeout=0.05))
    assert d.approved is False and d.decided_by == "timeout"


def test_killswitch_denied():
    KILLSWITCH.trigger("test")
    try:
        d = request_approval_sync(_req(), lambda r: True)
        assert d.approved is False and d.decided_by == "killswitch"
    finally:
        KILLSWITCH.reset()


def test_approver_error_denied():
    def boom(_):
        raise RuntimeError("x")

    d = request_approval_sync(_req(), boom)
    assert d.approved is False and d.decided_by == "error"
