"""shell_run — güvenli kabuk çalıştırma (B-05'in çözümü).

- Kara liste YOK, allowlist VAR (policy.yaml).
- Yorumlayıcı kaçışı (powershell/cmd/wsl) → RED.
- Zincirleme/yönlendirme → policy kararı confirm → onay modülü bağlanana kadar RED.
- Çıktı max_output_chars ile kesilir; sır kalıpları redakte edilir (B-16).
- Senkron çalışır; registry thread-pool'da koşturur (B-09).
"""
from __future__ import annotations

import re
import subprocess

from app.security.policy import DECISION_ALLOW, DECISION_DENY, load_policy
from app.tools.registry import Risk, ToolResult, tool

_POLICY = load_policy()

# Log redaksiyonu: anahtar/token kalıpları (§5.7)
_REDACT_RES = [
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{10,}"),
    re.compile(r"ya29\.[A-Za-z0-9_-]+"),
    re.compile(r"nvapi-[A-Za-z0-9_-]{8,}"),
]


def _redact(text: str) -> str:
    for rx in _REDACT_RES:
        text = rx.sub("***REDACTED***", text)
    return text


def _run_shell(command: str, timeout: int) -> ToolResult:
    decision, reason = _POLICY.check_shell(command)
    if decision == DECISION_DENY:
        return ToolResult(ok=False, message=f"Güvenlik: komut reddedildi ({reason}).",
                          error=f"policy_deny:{reason}")
    if decision != DECISION_ALLOW:
        return ToolResult(ok=False, message="Onay gerekli: kabuk komutu onaysız çalışmaz.",
                          error="confirmation_required")

    limit = _POLICY.shell.timeout_seconds
    try:
        timeout = max(1, min(int(timeout), limit))
    except (TypeError, ValueError):
        timeout = limit
    try:
        result = subprocess.run(
            command, shell=False, check=False, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return ToolResult(ok=False, message=f"Komut zaman aşımına uğradı ({timeout}s).",
                          error="timeout")
    except Exception as exc:
        return ToolResult(ok=False, message="Komut çalıştırılamadı.",
                          error=f"{type(exc).__name__}: {exc}")

    output = _redact((result.stdout + result.stderr).strip())
    max_chars = _POLICY.shell.max_output_chars
    if len(output) > max_chars:
        output = output[:max_chars] + "\n... (çıktı kısaltıldı)"
    if result.returncode != 0:
        return ToolResult(ok=False,
                          message=f"Komut hata koduyla bitti ({result.returncode}).",
                          error=f"exit:{result.returncode}", data={"output": output})
    if not output:
        return ToolResult(ok=True, message="Komut başarıyla çalıştı (çıktı yok).")
    return ToolResult(ok=True, message=output)


@tool(
    name="shell_run",
    description="İzinli listedeki güvenli kabuk komutlarını çalıştırır. Her çağrı policy'den geçer; onaysız çalışmaz.",
    risk=Risk.HIGH,
    requires_confirmation=True,
    params={
        "command": ("string", "Çalıştırılacak komut (tek komut, zincirleme yok)", True),
        "timeout": ("number", "Zaman aşımı sn (en fazla policy limiti)", False),
    },
    timeout=40.0,
)
def shell_run(command: str, timeout: int = 30) -> ToolResult:
    return _run_shell(command, timeout)
