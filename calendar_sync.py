"""Calendar integration: .ics export and optional Google Calendar API sync."""

import os
import socket
from datetime import datetime
from db import DATA_DIR

CREDENTIALS_PATH = os.path.join(DATA_DIR, "credentials.json")
TOKEN_PATH = os.path.join(DATA_DIR, "token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
GCAL_REQUEST_TIMEOUT = 20

OUTLOOK_TOKEN_CACHE_PATH = os.path.join(DATA_DIR, "outlook_token_cache.bin")
OUTLOOK_AUTHORITY = "https://login.microsoftonline.com/consumers"
OUTLOOK_SCOPES = ["https://graph.microsoft.com/Calendars.ReadWrite"]
OUTLOOK_EVENTS_URL = "https://graph.microsoft.com/v1.0/me/calendar/events"
OUTLOOK_REQUEST_TIMEOUT = 20


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


def has_gcal_token() -> bool:
    return os.path.exists(TOKEN_PATH)


def logout_gcal() -> bool:
    """Remove the locally saved Google OAuth token."""
    if not os.path.exists(TOKEN_PATH):
        return False
    os.remove(TOKEN_PATH)
    return True


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


# ── Outlook Calendar ──────────────────────────────────────────────────────────

def has_outlook_token() -> bool:
    return os.path.exists(OUTLOOK_TOKEN_CACHE_PATH)


def logout_outlook() -> bool:
    """Remove the locally saved Outlook OAuth token cache."""
    if not os.path.exists(OUTLOOK_TOKEN_CACHE_PATH):
        return False
    os.remove(OUTLOOK_TOKEN_CACHE_PATH)
    return True


def _load_outlook_cache():
    try:
        import msal
    except ImportError:
        raise RuntimeError("msal 库未安装，请运行 pip install msal")

    cache = msal.SerializableTokenCache()
    if os.path.exists(OUTLOOK_TOKEN_CACHE_PATH):
        with open(OUTLOOK_TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
            cache.deserialize(f.read())
    return cache


def _save_outlook_cache(cache):
    if cache.has_state_changed:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTLOOK_TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(cache.serialize())


def _get_outlook_token(client_id: str, interactive: bool = False) -> str:
    client_id = (client_id or "").strip()
    if not client_id:
        raise RuntimeError("请先填写 Outlook Client ID。")

    try:
        import msal
    except ImportError:
        raise RuntimeError("msal 库未安装，请运行 pip install msal")

    cache = _load_outlook_cache()
    app = msal.PublicClientApplication(
        client_id,
        authority=OUTLOOK_AUTHORITY,
        token_cache=cache,
    )

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(OUTLOOK_SCOPES, account=accounts[0])

    if not result and interactive:
        result = app.acquire_token_interactive(scopes=OUTLOOK_SCOPES)

    _save_outlook_cache(cache)

    if result and "access_token" in result:
        return result["access_token"]

    if interactive and result:
        detail = result.get("error_description") or result.get("error") or str(result)
        raise RuntimeError(f"Outlook 授权失败：{detail}")

    raise RuntimeError("Outlook 账户未连接，请先点击“连接 Outlook”。")


def connect_outlook(client_id: str) -> str:
    """Open browser auth for Outlook and return the signed-in account label."""
    token = _get_outlook_token(client_id, interactive=True)
    if token:
        return "Outlook 账户"
    return ""


def sync_session_to_outlook(session: dict, client_id: str) -> str:
    """Create an Outlook Calendar event for the session. Returns event id."""
    try:
        import requests
    except ImportError:
        raise RuntimeError("requests 库未安装，请运行 pip install requests")

    access_token = _get_outlook_token(client_id, interactive=False)

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

    mode_label = {"25min": "25分钟", "custom": "自定义", "countup": "正计时"}.get(
        session.get("mode", ""), session.get("mode", "")
    )
    description += f"\n模式：{mode_label}"

    body = {
        "subject": session.get("note") or "番茄时钟",
        "body": {
            "contentType": "text",
            "content": description.strip(),
        },
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Shanghai",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Shanghai",
        },
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        OUTLOOK_EVENTS_URL,
        headers=headers,
        json=body,
        timeout=OUTLOOK_REQUEST_TIMEOUT,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Outlook API 返回 {response.status_code}：{response.text}")
    return response.json().get("id", "")


def format_outlook_error(exc: Exception) -> str:
    """Return a user-facing Outlook Calendar error message."""
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
            "连接 Outlook Calendar API 超时。\n\n"
            "请确认当前网络可以访问 login.microsoftonline.com / graph.microsoft.com，"
            "并检查系统代理、防火墙或 VPN 设置后重试。\n\n"
            f"原始错误：{raw}"
        )

    if isinstance(exc, OSError) or any(m in raw for m in connection_markers):
        return (
            "无法连接到 Outlook Calendar API。\n\n"
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


OUTLOOK_SETUP_INSTRUCTIONS = """如何配置 Outlook Calendar 同步：

1. 打开 Microsoft Azure Portal：
   https://portal.azure.com/

2. 进入 Microsoft Entra ID → 应用注册 → 新注册

3. 支持的账户类型选择：
   个人 Microsoft 账户

4. 添加平台：
   身份验证 → 添加平台 → 移动和桌面应用程序
   勾选 http://localhost

5. API 权限：
   Microsoft Graph → 委托权限 → Calendars.ReadWrite

6. 复制“应用程序(客户端) ID”，填入本应用的 Outlook Client ID。

7. 回到本应用，点击“连接 Outlook”，浏览器会打开授权页面。

授权完成后，每次番茄钟结束时会自动同步到 Outlook 默认日历。
"""
