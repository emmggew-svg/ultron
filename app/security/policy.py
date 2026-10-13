"""Policy Engine — spec §5.2 (B-05'in çözümü: allowlist esastır).

Karar kümesi: "allow" | "confirm" | "deny".
- Tanımsız araç/komut → deny (default-deny).
- Kabuk: komut AYRIŞTIRILIR; zincirleme (&& ; | `) veya yönlendirme (>)
  varsa en yüksek risk → confirm/deny. Yasak kalıp varsa → deny.
- Yollar: Path.resolve() ile gerçek yol; allowed_roots içinde ve
  denied_roots dışında olmalı. `..`, symlink, UNC kaçışları resolve ile çöker.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
    _HAS_YAML = True
except Exception:
    _HAS_YAML = False

DECISION_ALLOW = "allow"
DECISION_CONFIRM = "confirm"
DECISION_DENY = "deny"

# Zincirleme / yönlendirme / komut-değiştirme belirtileri
_CHAIN_RES = [
    re.compile(r"&&|\|\|"),
    re.compile(r"(?<![|>])\|(?![|>])"),   # tek pipe (|| hariç)
    re.compile(r";"),
    re.compile(r"`"),
    re.compile(r"\$\("),
    re.compile(r"[<>]"),                  # yönlendirme
]


@dataclass
class ShellPolicy:
    mode: str = "allowlist"
    allowed_commands: list[str] = field(default_factory=list)
    forbid_patterns: list[str] = field(default_factory=list)
    always_confirm: bool = True
    timeout_seconds: int = 30
    max_output_chars: int = 4000


@dataclass
class Policy:
    default_decision: str = DECISION_DENY
    allowed_roots: list[str] = field(default_factory=list)
    denied_roots: list[str] = field(default_factory=list)
    shell: ShellPolicy = field(default_factory=ShellPolicy)

    # -- yollar --
    def _expand(self, raw: str) -> Path:
        return Path(os.path.expandvars(raw)).resolve()

    def _roots(self, roots: list[str]) -> list[Path]:
        out = []
        for r in roots:
            try:
                out.append(self._expand(r))
            except Exception:
                continue
        return out

    @staticmethod
    def _inside(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def check_path(self, raw_path: str) -> str:
        """Dosya yolu kararı: allow | deny."""
        try:
            path = (Path(os.path.expandvars(raw_path))).resolve()
        except Exception:
            return DECISION_DENY
        # UNC ve sürücüsüz göreli kaçışlar resolve sonrası mutlaktır; yine de UNC'yi reddet
        if str(raw_path).startswith("\\\\"):
            return DECISION_DENY
        for denied in self._roots(self.denied_roots):
            if self._inside(path, denied) or path == denied:
                return DECISION_DENY
        for allowed in self._roots(self.allowed_roots):
            if self._inside(path, allowed) or path == allowed:
                return DECISION_ALLOW
        return DECISION_DENY  # liste dışı = ret

    # -- kabuk --
    @staticmethod
    def _first_token(command: str) -> str:
        cmd = command.strip().strip('"').strip("'")
        # powershell.exe -Command "..." gibi çağrılarda gerçek komutu bulmak Faz 2 işi;
        # Faz 1: ilk token; powershell/cmd ise deny (yorumlayıcı kaçışı).
        token = cmd.split(None, 1)[0] if cmd.split() else ""
        token = os.path.basename(token).lower()
        if token.endswith(".exe"):
            token = token[:-4]
        return token

    def check_shell(self, command: str) -> tuple[str, str]:
        """(karar, gerekçe). Faz 1 kural seti: allowlist + forbid + zincir escalasyonu."""
        if not command or not command.strip():
            return DECISION_DENY, "boş komut"
        lowered = command.lower()

        for pat in self.shell.forbid_patterns:
            if pat.lower() in lowered:
                return DECISION_DENY, f"yasak kalıp: {pat}"

        chained = any(rx.search(command) for rx in _CHAIN_RES)
        token = self._first_token(command)
        if token in ("powershell", "pwsh", "cmd", "wsl", "bash", "sh"):
            return DECISION_DENY, f"yorumlayıcı üzerinden çalıştırma yasak: {token}"
        if self.shell.mode == "allowlist" and token not in [c.lower() for c in self.shell.allowed_commands]:
            return DECISION_DENY, f"allowlist dışı komut: {token}"
        if chained:
            # Zincirli komut en yüksek risk: allowlist'te olsa bile onay ister
            return DECISION_CONFIRM, "zincirleme/yönlendirme içeriyor"
        if self.shell.always_confirm:
            return DECISION_CONFIRM, "shell her zaman onay ister"
        return DECISION_ALLOW, "allowlist"

    def check_tool(self, risk: str, requires_confirmation: bool) -> str:
        if risk in ("HIGH", "CRITICAL"):
            return DECISION_CONFIRM
        if requires_confirmation:
            return DECISION_CONFIRM
        return DECISION_ALLOW


def _defaults() -> Policy:
    return Policy(
        default_decision=DECISION_DENY,
        allowed_roots=[
            "%USERPROFILE%\\Documents", "%USERPROFILE%\\Desktop",
            "%USERPROFILE%\\Downloads", "%USERPROFILE%\\ultron_workspace",
        ],
        denied_roots=[
            "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
            "%APPDATA%\\ultron\\secrets", "%USERPROFILE%\\.ssh",
        ],
        shell=ShellPolicy(
            allowed_commands=["dir", "type", "where", "echo", "git", "python",
                              "pip", "node", "npm", "ipconfig", "tasklist", "whoami"],
            forbid_patterns=["-EncodedCommand", "Invoke-Expression", "iex ",
                             "DownloadString", "Remove-Item -Recurse", "format ",
                             "diskpart", "bcdedit", "reg add", "reg delete",
                             "net user", "schtasks /create"],
            always_confirm=True, timeout_seconds=30, max_output_chars=4000,
        ),
    )


def load_policy(path: str | Path | None = None) -> Policy:
    """policy.yaml'ı okur; PyYAML yoksa/bozuksa güvenli varsayılanlara düşer."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "policy.yaml"
    if _HAS_YAML:
        try:
            data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
            sh = data.get("shell", {}) or {}
            return Policy(
                default_decision=data.get("default_decision", DECISION_DENY),
                allowed_roots=list(data.get("allowed_roots", [])),
                denied_roots=list(data.get("denied_roots", [])),
                shell=ShellPolicy(
                    mode=sh.get("mode", "allowlist"),
                    allowed_commands=list(sh.get("allowed_commands", [])),
                    forbid_patterns=list(sh.get("forbid_patterns", [])),
                    always_confirm=bool(sh.get("always_confirm", True)),
                    timeout_seconds=int(sh.get("timeout_seconds", 30)),
                    max_output_chars=int(sh.get("max_output_chars", 4000)),
                ),
            )
        except Exception:
            pass
    return _defaults()
