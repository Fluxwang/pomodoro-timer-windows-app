import threading
import time
from enum import Enum
from datetime import datetime


class TimerMode(Enum):
    COUNTDOWN_25 = "25min"
    COUNTDOWN_CUSTOM = "custom"
    COUNTUP = "countup"


class TimerState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class PomodoroTimer:
    def __init__(self):
        self.mode = TimerMode.COUNTDOWN_25
        self.state = TimerState.IDLE
        self.custom_duration = 25 * 60  # seconds

        self.elapsed = 0
        self.total = 25 * 60
        self.start_time: datetime | None = None

        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()

        self.current_note = ""
        self.current_tags: list[str] = []

        # Callbacks — set by the App controller
        self.on_tick = None          # (elapsed, total, remaining) → None
        self.on_finish = None        # (session_data: dict) → None
        self.on_state_change = None  # (TimerState) → None

    # ── Public API ────────────────────────────────────────────────────────────

    def set_mode(self, mode: TimerMode, custom_minutes: int = 25):
        if self.state != TimerState.IDLE:
            return
        self.mode = mode
        self.custom_duration = custom_minutes * 60
        self.total = self._calc_total()

    def start(self, note: str = "", tags: list[str] | None = None):
        if self.state == TimerState.RUNNING:
            return
        self.current_note = note
        self.current_tags = tags or []
        self.start_time = datetime.now()

        if self.state == TimerState.IDLE:
            self.elapsed = 0
            self.total = self._calc_total()

        self.state = TimerState.RUNNING
        self._stop_event.clear()
        self._pause_event.set()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._emit_state()

    def pause(self):
        if self.state != TimerState.RUNNING:
            return
        self.state = TimerState.PAUSED
        self._pause_event.clear()
        self._emit_state()

    def resume(self):
        if self.state != TimerState.PAUSED:
            return
        self.state = TimerState.RUNNING
        self._pause_event.set()
        self._emit_state()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()
        self.state = TimerState.IDLE
        self.elapsed = 0
        self._emit_state()

    def toggle_pause(self):
        if self.state == TimerState.RUNNING:
            self.pause()
        elif self.state == TimerState.PAUSED:
            self.resume()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _calc_total(self) -> int:
        if self.mode == TimerMode.COUNTDOWN_25:
            return 25 * 60
        if self.mode == TimerMode.COUNTDOWN_CUSTOM:
            return self.custom_duration
        return 0  # COUNTUP has no fixed total

    def _run(self):
        while not self._stop_event.is_set():
            self._pause_event.wait(timeout=1)
            if self._stop_event.is_set():
                break
            if not self._pause_event.is_set():
                continue

            time.sleep(1)

            if self._stop_event.is_set() or not self._pause_event.is_set():
                continue

            self.elapsed += 1

            if self.mode in (TimerMode.COUNTDOWN_25, TimerMode.COUNTDOWN_CUSTOM):
                remaining = max(0, self.total - self.elapsed)
                if self.on_tick:
                    self.on_tick(self.elapsed, self.total, remaining)
                if remaining <= 0:
                    self._finish()
                    return
            else:
                if self.on_tick:
                    self.on_tick(self.elapsed, 0, self.elapsed)

    def _finish(self):
        self.state = TimerState.FINISHED
        end_time = datetime.now()
        session_data = {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": end_time.isoformat(),
            "planned_duration": self.total,
            "actual_duration": self.elapsed,
            "mode": self.mode.value,
            "note": self.current_note,
            "tags": self.current_tags,
            "completed": True,
        }
        if self.on_finish:
            self.on_finish(session_data)
        self.state = TimerState.IDLE
        self.elapsed = 0
        self._emit_state()

    def _emit_state(self):
        if self.on_state_change:
            self.on_state_change(self.state)
