"""Hafıza araçları — LOW. Hassas bilgi reddedilir; yazım atomiktir (B-14/B-17)."""
from __future__ import annotations

from app.memory.store import contains_sensitive, load, update
from app.tools.registry import Risk, ToolResult, tool


@tool(name="save_memory",
      description="Kullanıcı hakkında önemli bilgiyi kalıcı belleğe kaydeder.",
      risk=Risk.LOW,
      params={
          "category": ("string", "Kategori (örn. tercihler, kişiler)", True),
          "key": ("string", "Anahtar", True),
          "value": ("string", "Değer", True),
      })
def save_memory(category: str, key: str, value: str) -> ToolResult:
    if not (category or "").strip() or not (key or "").strip():
        return ToolResult(ok=False, message="Kategori ve anahtar gerekli.", error="bad_args")
    if contains_sensitive(f"{key} {value}"):
        return ToolResult(ok=False, message="Hassas bilgi hafızaya yazılamaz.",
                          error="sensitive_rejected")
    try:
        update({category.strip(): {key.strip(): {"value": value}}})
    except Exception as exc:
        return ToolResult(ok=False, message="Hafıza yazılamadı.", error=str(exc))
    return ToolResult(ok=True, message=f"Kaydedildi: {category}/{key}")


@tool(name="delete_memory",
      description="Hafızadaki bir kaydı siler (category/key veya metin eşleşmesi).",
      risk=Risk.LOW,
      params={
          "category": ("string", "Kategori", False),
          "key": ("string", "Anahtar", False),
          "match_text": ("string", "Aranacak metin", False),
      })
def delete_memory(category: str = "", key: str = "", match_text: str = "") -> ToolResult:
    from app.memory.store import save as _save

    mem = load()
    if not mem:
        return ToolResult(ok=True, message="Hafıza zaten boş.")
    category, key, match_text = (category or "").strip(), (key or "").strip(), (match_text or "").strip()
    try:
        if category and key:
            bucket = mem.get(category)
            if isinstance(bucket, dict) and key in bucket:
                del bucket[key]
                if not bucket:
                    mem.pop(category, None)
                _save(mem)
                return ToolResult(ok=True, message=f"{category}/{key} silindi.")
            return ToolResult(ok=False, message="Kayıt bulunamadı.", error="not_found")
        needle = (match_text or key).casefold()
        if not needle:
            return ToolResult(ok=False, message="category/key veya match_text gerekli.",
                              error="bad_args")
        for cat, bucket in list(mem.items()):
            if isinstance(bucket, dict):
                for ik, iv in list(bucket.items()):
                    hay = f"{cat} {ik} {iv}".casefold()
                    if needle in hay:
                        del bucket[ik]
                        if not bucket:
                            mem.pop(cat, None)
                        _save(mem)
                        return ToolResult(ok=True, message=f"{cat}/{ik} silindi.")
            elif needle in f"{cat} {bucket}".casefold():
                del mem[cat]
                _save(mem)
                return ToolResult(ok=True, message=f"{cat} silindi.")
        return ToolResult(ok=False, message="Eşleşen kayıt bulunamadı.", error="not_found")
    except Exception as exc:
        return ToolResult(ok=False, message="Silme başarısız.", error=str(exc))
