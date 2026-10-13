"""Sır yönetimi — spec §5.7. Windows Credential Manager (keyring) sarmalayıcı.

- API anahtarları / OAuth token'ları SADECE burada durur; `config/api_keys.json` ÖLÜDÜR.
- keyring yoksa: yazma REDDEDİLİR (güvenli varsayılan), okuma None döner.
  Sessizce düz-metne düşmek YASAKTIR.
- İlk kurulumda eski `api_keys.json` varsa içe aktarılıp SİLİNİR (migrate_legacy).
"""
from __future__ import annotations

import json
from pathlib import Path

SERVICE_NAME = "ULTRON"

try:
    import keyring  # type: ignore[import-not-found]
    _HAS_KEYRING = True
except Exception:
    keyring = None  # type: ignore[assignment]
    _HAS_KEYRING = False


class SecretsUnavailable(Exception):
    """keyring yokken yazma denendi."""


def backend_available() -> bool:
    if not _HAS_KEYRING:
        return False
    try:
        kr = keyring.get_keyring()
        return getattr(kr, "priority", 0) > 0
    except Exception:
        return False


def set_secret(name: str, value: str) -> None:
    if not _HAS_KEYRING or not backend_available():
        raise SecretsUnavailable(
            "keyring kullanılamıyor — sır düz metne yazılmayacak, işlem reddedildi.")
    keyring.set_password(SERVICE_NAME, name, value)


def get_secret(name: str) -> str | None:
    if not _HAS_KEYRING or not backend_available():
        return None
    try:
        return keyring.get_password(SERVICE_NAME, name)
    except Exception:
        return None


def delete_secret(name: str) -> bool:
    if not _HAS_KEYRING or not backend_available():
        return False
    try:
        keyring.delete_password(SERVICE_NAME, name)
        return True
    except Exception:
        return False


def migrate_legacy(config_path: str | Path) -> list[str]:
    """Eski config/api_keys.json'u keyring'e taşır, dosyayı SİLER. Taşınan adları döner."""
    path = Path(config_path)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    moved: list[str] = []
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, str) and value.strip():
                try:
                    set_secret(str(key), value)
                    moved.append(str(key))
                except SecretsUnavailable:
                    break
    if moved:
        try:
            path.unlink()
        except Exception:
            pass
    return moved
