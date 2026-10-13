"""Gizlilik testleri — spec §5.7: sırlar koda/loga girmez, örnek config'ler boştur."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

_KEY_RES = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{16,}"),
    re.compile(r"ya29\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"nvapi-[A-Za-z0-9_-]{16,}"),
]

# Bu dosyaların kendisi test amaçlı sahte değer içerir + legacy referanslar:
_EXCLUDE = {"test_privacy.py", "test_shell_tool.py", "test_secrets.py"}


def test_no_real_keys_in_app_code():
    hits = []
    for path in list((ROOT / "app").rglob("*.py")) + list((ROOT / "tests").rglob("*.py")):
        if path.name in _EXCLUDE:
            continue
        text = path.read_text(encoding="utf-8")
        for rx in _KEY_RES:
            if rx.search(text):
                hits.append(f"{path.name}: {rx.pattern}")
    assert hits == [], f"sır kalıbı bulundu: {hits}"


def test_example_configs_have_no_secrets():
    import re as _re
    secret_key = _re.compile(r"(key|token|secret|password|passwd|auth|credential)", _re.IGNORECASE)
    for rel in ("legacy/jarvis-windows/config/api_keys.example.json",
                "legacy/v2-windows/config/api_keys.example.json"):
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for k, v in data.items():
            if secret_key.search(k):
                assert not (isinstance(v, str) and v.strip()), f"{rel}:{k} dolu!"


def test_audit_redaction_covers_password_variants():
    from app.security.audit import redact_args

    clean = redact_args({"user_password": "x", "passwd": "y", "authToken": "z", "normal": "ok"})
    assert clean["user_password"] == "***REDACTED***"
    assert clean["passwd"] == "***REDACTED***"
    assert clean["authToken"] == "***REDACTED***"
    assert clean["normal"] == "ok"
