"""Google Calendar OAuth + API istemcisi — Faz 3."""

from __future__ import annotations

import datetime
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    _HAS_GOOGLE_API = True
except ImportError:
    _HAS_GOOGLE_API = False

from app.tools.registry import Risk, ToolResult, tool

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_DIR = Path(__file__).resolve().parent.parent / "data" / "google"
TOKEN_FILE = TOKEN_DIR / "token.json"
CREDS_FILE = TOKEN_DIR / "credentials.json"


def ensure_token_dir() -> None:
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)


def get_credentials() -> Credentials | None:
    """OAuth akışı (ilk çalışmada) ya da saklı token ile Credentials döner."""
    if not _HAS_GOOGLE_API:
        return None
    ensure_token_dir()
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds:
            if not CREDS_FILE.exists():
                raise FileNotFoundError(
                    f"Google OAuth credentials.json eksik: {CREDS_FILE}. "
                    "Google Cloud Console'dan OAuth Client ID (Desktop) indirip koyun.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def get_calendar_service():
    """Google Calendar API servisi (build + credentials)."""
    creds = get_credentials()
    if creds is None:
        return None
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def parse_datetime_iso(value: str) -> datetime.datetime | None:
    """ISO veya 'YYYY-MM-DD HH:MM' formatını parse eder; tz yoksa yerel."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
            return dt
        except ValueError:
            continue
    return None


def format_for_gcal(dt: datetime.datetime) -> str:
    """Calendar API'sinin beklediği RFC3339 formatı (Z veya offset)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
    return dt.isoformat()


# --- Calendar Tools ---

@tool(
    name="calendar_list",
    description="Google Calendar etkinliklerini listeler. time_min/max ile aralık verilebilir.",
    risk=Risk.SAFE,
    params={
        "time_min": ("string", "Başlangıç (ISO), boşsa şimdi", False),
        "time_max": ("string", "Bitiş (ISO), boşsa +7 gün", False),
        "max_results": ("number", "Maksimum sonuç", False),
    })
def calendar_list(time_min: str = "", time_max: str = "", max_results: int = 10) -> ToolResult:
    if not _HAS_GOOGLE_API:
        return ToolResult(ok=False, message="Google API kütüphanesi yok.", error="missing_deps")
    service = get_calendar_service()
    if service is None:
        return ToolResult(ok=False, message="Calendar servisi kullanılamıyor (OAuth gerekli).", error="no_service")
    try:
        now = datetime.datetime.now(datetime.UTC)
        tmin = parse_datetime_iso(time_min) if time_min else now
        tmax = parse_datetime_iso(time_max) if time_max else (now + datetime.timedelta(days=7))
        if tmin is None or tmax is None:
            return ToolResult(ok=False, message="Geçersiz tarih formatı.", error="bad_args")
        events_result = service.events().list(
            calendarId="primary",
            timeMin=format_for_gcal(tmin),
            timeMax=format_for_gcal(tmax),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        if not events:
            return ToolResult(ok=True, message="Bu aralıkta etkinlik yok.")
        lines = []
        for ev in events:
            start = ev["start"].get("dateTime", ev["start"].get("date"))
            summary = ev.get("summary", "(başlıksız)")
            lines.append(f"{start} — {summary}")
        return ToolResult(ok=True, message="\n".join(lines))
    except Exception as exc:
        return ToolResult(ok=False, message="Calendar okunamadı.", error=str(exc))


@tool(
    name="calendar_create",
    description="Google Calendar'a yeni etkinlik ekler. Başlık, başlangıç (ISO) zorunlu.",
    risk=Risk.MEDIUM,
    params={
        "summary": ("string", "Etkinlik başlığı", True),
        "start_iso": ("string", "Başlangıç (ISO)", True),
        "end_iso": ("string", "Bitiş (ISO), boşsa +1 saat", False),
        "description": ("string", "Açıklama", False),
        "location": ("string", "Konum", False),
    })
def calendar_create(summary: str, start_iso: str, end_iso: str = "", description: str = "", location: str = "") -> ToolResult:
    if not _HAS_GOOGLE_API:
        return ToolResult(ok=False, message="Google API kütüphanesi yok.", error="missing_deps")
    service = get_calendar_service()
    if service is None:
        return ToolResult(ok=False, message="Calendar servisi kullanılamıyor.", error="no_service")
    start_dt = parse_datetime_iso(start_iso)
    if start_dt is None:
        return ToolResult(ok=False, message="Başlangıç tarihi anlaşılmadı.", error="bad_args")
    if end_iso:
        end_dt = parse_datetime_iso(end_iso)
        if end_dt is None:
            return ToolResult(ok=False, message="Bitiş tarihi anlaşılmadı.", error="bad_args")
        if end_dt <= start_dt:
            return ToolResult(ok=False, message="Bitiş başlangıçtan sonra olmalı.", error="bad_args")
    else:
        end_dt = start_dt + datetime.timedelta(hours=1)
    try:
        event = {
            "summary": summary,
            "start": {"dateTime": format_for_gcal(start_dt), "timeZone": str(datetime.datetime.now().astimezone().tzinfo)},
            "end": {"dateTime": format_for_gcal(end_dt), "timeZone": str(datetime.datetime.now().astimezone().tzinfo)},
        }
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        created = service.events().insert(calendarId="primary", body=event).execute()
        return ToolResult(ok=True, message=f"Etkinlik oluşturuldu: {created.get('htmlLink', 'link yok')}")
    except Exception as exc:
        return ToolResult(ok=False, message="Etkinlik oluşturulamadı.", error=str(exc))


@tool(
    name="calendar_delete",
    description="Google Calendar'dan etkinlik siler (event_id ile).",
    risk=Risk.HIGH,
    requires_confirmation=True,
    params={
        "event_id": ("string", "Silinecek etkinlik ID", True),
    })
def calendar_delete(event_id: str) -> ToolResult:
    if not _HAS_GOOGLE_API:
        return ToolResult(ok=False, message="Google API kütüphanesi yok.", error="missing_deps")
    service = get_calendar_service()
    if service is None:
        return ToolResult(ok=False, message="Calendar servisi kullanılamıyor.", error="no_service")
    if not event_id or not event_id.strip():
        return ToolResult(ok=False, message="event_id gerekli.", error="bad_args")
    try:
        service.events().delete(calendarId="primary", eventId=event_id.strip()).execute()
        return ToolResult(ok=True, message="Etkinlik silindi.")
    except Exception as exc:
        return ToolResult(ok=False, message="Silme başarısız.", error=str(exc))