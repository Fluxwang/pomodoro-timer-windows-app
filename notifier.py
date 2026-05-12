import subprocess
import sys


def notify(title: str, message: str):
    """Send a Windows desktop notification. Falls back gracefully."""
    if _try_plyer(title, message):
        return
    _try_powershell(title, message)


def _try_plyer(title: str, message: str) -> bool:
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="番茄时钟",
            timeout=8,
        )
        return True
    except Exception:
        return False


def _try_powershell(title: str, message: str):
    # Escape single quotes for PowerShell
    t = title.replace("'", "''")
    m = message.replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        "$n.Visible = $true;"
        f"$n.ShowBalloonTip(6000,'{t}','{m}',"
        "[System.Windows.Forms.ToolTipIcon]::None);"
        "Start-Sleep -Seconds 7;"
        "$n.Dispose()"
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
