"""Araç yükleyici — tüm @tool modüllerini import edip registry'e kaydeder.

Testler ve ajan çekirdeği bunu kullanır; böylece "import edilmemiş araç"
sınıfı hatalar ortadan kalkar.
"""
from __future__ import annotations

from app.tools.registry import ToolRegistry, get_registry


def load_all(registry: ToolRegistry | None = None) -> ToolRegistry:
    import app.tools.comms_tools
    import app.tools.memory_tools
    import app.tools.shell_tool
    import app.tools.system_tools
    import app.tools.task_tools
    import app.tools.web_tools  # noqa: F401

    return registry or get_registry()
