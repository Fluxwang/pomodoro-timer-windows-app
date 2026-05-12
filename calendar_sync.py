"""Calendar integration: .ics export and optional Google Calendar API sync."""

import os
import socket
from datetime import datetime, timezone
from db import DATA_DIR

CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
GCAL_REQUEST_TIMEOUT = 20


# ── .ics Export ───────────────────────────────────────────────────────────────

def sessions_to_ics(sessions: list[dict]) -> bytes:
    """Convert session records to iCalendar (.ics) bytes."""
    try:
        from icalendar import Calendar, Event, vText, vDatetime
    except ImportError:
        raise RuntimeError("icalendar 库未安装，请运行 pip install icalendar")

    cal = Calendar()
    cal.add("prodid", "-//番茄时钟//pomodoro//ZH")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "番茄时钟")

    for s in sessions:
        if not s.get("start_time"):
            continue
        event = Event()

        start_dt = datetime.fromisoformat(s["start_time"])
        end_dt = (
            datetime.fromisoformat(s["end_time"])
            if s.get("end_time")
            else start_dt
        )

        summary = s.get("note") or "番茄时钟"
        tags = s.get("tags", [])
        description = ""
        if tags:
            description += "标签：" + "、".join(tags) + "\n"
        if s.get("note"):
            description += s["note"]

        mode_label = {"25min": "25分钟", "custom": "自定义", "countup": "正计时"}.get(
            s.get("mode", ""), s.get("mode", "")
        )
        description += f"\n模式：{mode_label}"

        event.add("summary", summary)
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        if description:
            event.add("description", description.strip())

        cal.add_component(event)

    return cal.to_ical()


def export_ics_file(sessions: list[dict], path: str):
    data = sessions_to_ics(sessions)
    with open(path, "wb") as f:
        f.write(data)


# ── Google Calendar ───────────────────────────────────────────────────────────

def has_credentials() -> bool:
    return os.path.exists(CREDENTIALS_PATH)


def get_gcal_service():
    """Return an authenticated Google Calendar service, or raise."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    try:
        import httplib2
        from google_auth_httplib2 import AuthorizedHttp

        http = AuthorizedHttp(
            creds,
            http=httplib2.Http(timeout=GCAL_REQUEST_TIMEOUT),
        )
        return build("calendar", "v3", http=http, cache_discovery=False)
    except ImportError:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)


def sync_session_to_gcal(session: dict, calendar_id: str = "primary") -> str:
    """Create a Google Calendar event for the session. Returns event id."""
    service = get_gcal_service()

    start_dt = datetime.fromisoformat(session["start_time"])
    end_dt = (
        datetime.fromisoformat(session["end_time"])
        if session.get("end_time")
        else start_dt
    )

    tags = session.get("tags", [])
    description = ""
    if tags:
        description += "标签：" + "、".join(tags) + "\n"
    if session.get("note"):
        description += session["note"]

    body = {
        "summary": session.get("note") or "番茄时钟",
        "description": description.strip(),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Shanghai"},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": "Asia/Shanghai"},
    }
    result = service.events().insert(calendarId=calendar_id, body=body).execute()
    return result.get("id", "")


def format_gcal_error(exc: Exception) -> str:
    """Return a user-facing Google Calendar error message."""
    raw = str(exc) or exc.__class__.__name__
    timeout_markers = (
        "timed out",
        "timeout",
        "WinError 10060",
        "Errno 110",
        "Errno 10060",
    )
    connection_markers = (
        "Failed to establish a new connection",
        "NameResolutionError",
        "getaddrinfo failed",
        "Network is unreachable",
        "Connection refused",
    )

    if isinstance(exc, (TimeoutError, socket.timeout)) or any(m in raw for m in timeout_markers):
        return (
            "连接 Google Calendar API 超时。\n\n"
            "请确认当前网络可以访问 googleapis.com / accounts.google.com，"
            "并检查系统代理、防火墙或 VPN 设置后重试。\n\n"
            f"原始错误：{raw}"
        )

    if isinstance(exc, OSError) or any(m in raw for m in connection_markers):
        return (
            "无法连接到 Google Calendar API。\n\n"
            "请检查网络连接、DNS、系统代理、防火墙或 VPN 设置。"
            "如果你在受限网络环境中，需要先让系统代理对本应用生效。\n\n"
            f"原始错误：{raw}"
        )

    return raw


GCAL_SETUP_INSTRUCTIONS = """如何配置 Google Calendar 同步：

1. 打开 Google Cloud Console：
   https://console.cloud.google.com/

2. 创建项目（或选择现有项目）

3. 启用 Google Calendar API：
   API 和服务 → 库 → 搜索 "Google Calendar API" → 启用

4. 创建 OAuth 2.0 凭据：
   API 和服务 → 凭据 → 创建凭据 → OAuth 客户端 ID
   应用类型选择：桌面应用

5. 下载 JSON 文件，重命名为 credentials.json

6. 将 credentials.json 放入：
   {data_dir}

7. 回到此应用，点击"连接账户"，浏览器会打开授权页面

授权完成后，每次番茄钟结束时会自动同步到 Google Calendar。
""".format(data_dir=DATA_DIR)
