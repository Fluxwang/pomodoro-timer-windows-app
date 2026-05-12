"""Pomodoro Timer — entry point and application controller."""

import sys
import os
import threading

import customtkinter as ctk

from db import Database
from timer import PomodoroTimer, TimerMode, TimerState
from tray import SystemTray
import notifier


def get_exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(__file__)


def set_windows_startup(enable: bool, app_name: str = "PomodoroTimer"):
    """Add or remove the app from Windows startup via registry."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
        )
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, get_exe_path())
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass  # Not on Windows or access denied


class App:
    """Central controller — owns all subsystems."""

    def __init__(self):
        self.db = Database()
        self.timer = PomodoroTimer()

        # Restore custom duration from settings
        custom_min = int(self.db.get_setting("custom_duration", "25"))
        self.timer.custom_duration = custom_min * 60

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        from ui import MainWindow
        self.window = MainWindow(self)

        # Wire timer callbacks (all routed through main thread via window.after)
        self.timer.on_tick = self._on_tick
        self.timer.on_finish = self._on_finish
        self.timer.on_state_change = self._on_state_change

        self.tray = SystemTray(self)
        self._tray_thread = threading.Thread(target=self.tray.run, daemon=True)
        self._tray_thread.start()

    # ── Timer callbacks ───────────────────────────────────────────────────────

    def _on_tick(self, elapsed: int, total: int, display_val: int):
        self.window.after(0, lambda: self.window.update_display(elapsed, total, display_val))

    def _on_state_change(self, state: TimerState):
        tray_state = {
            TimerState.RUNNING: "running",
            TimerState.PAUSED: "paused",
        }.get(state, "idle")
        self.tray.set_state(tray_state)
        self.window.after(0, lambda: self.window.on_state_change(state))

    def _on_finish(self, session_data: dict):
        # Save to DB
        session_id = self.db.save_session(session_data)

        # Send notification
        note_preview = session_data.get("note", "") or "专注时段"
        notifier.notify("🍅 番茄钟完成！", note_preview[:60])

        # Optional Google Calendar sync
        if self.db.get_setting("gcal_enabled", "false") == "true":
            cal_id = self.db.get_setting("gcal_calendar_id", "primary")
            threading.Thread(
                target=self._sync_gcal, args=(session_data, cal_id), daemon=True
            ).start()

        if self.db.get_setting("outlook_enabled", "false") == "true":
            client_id = self.db.get_setting("outlook_client_id", "")
            threading.Thread(
                target=self._sync_outlook, args=(session_data, client_id), daemon=True
            ).start()

    def _sync_gcal(self, session_data: dict, calendar_id: str):
        try:
            from calendar_sync import format_gcal_error, sync_session_to_gcal
            sync_session_to_gcal(session_data, calendar_id)
        except Exception as e:
            print(f"[Google Calendar] 同步失败: {format_gcal_error(e)}", file=sys.stderr)

    def _sync_outlook(self, session_data: dict, client_id: str):
        try:
            from calendar_sync import format_outlook_error, sync_session_to_outlook
            sync_session_to_outlook(session_data, client_id)
        except Exception as e:
            print(f"[Outlook Calendar] 同步失败: {format_outlook_error(e)}", file=sys.stderr)

    # ── Public API (called from tray / UI) ───────────────────────────────────

    def start_timer(self, note: str = "", tags: list[str] | None = None):
        self.timer.start(note=note, tags=tags or [])

    def quick_start_25(self):
        """Start a 25-min timer from the tray menu (no note dialog)."""
        self.timer.set_mode(TimerMode.COUNTDOWN_25)
        self.timer.start(note="", tags=[])
        self.window.after(0, self.window.show)

    def show_window(self):
        self.window.after(0, self.window.show)

    def set_startup(self, enable: bool):
        set_windows_startup(enable)

    def quit(self):
        self.timer.stop()
        self.tray.stop()
        self.window.after(0, self.window.destroy)

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()
