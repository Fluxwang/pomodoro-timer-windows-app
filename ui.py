"""All UI components: MainWindow, NoteDialog, HistoryPanel, SettingsDialog."""

import os
import sys
import threading
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from tkinter import filedialog, messagebox

from timer import TimerMode, TimerState

# ── Palette ───────────────────────────────────────────────────────────────────
ACCENT = "#e94560"
ACCENT_HOVER = "#c73250"
BG_CARD = "#1e1e2e"
TEXT_DIM = "#888888"

MODE_LABELS = {
    TimerMode.COUNTDOWN_25: "25 分钟",
    TimerMode.COUNTDOWN_CUSTOM: "自定义",
    TimerMode.COUNTUP: "正计时",
}
MODE_BY_LABEL = {v: k for k, v in MODE_LABELS.items()}


def fmt_time(seconds: int) -> str:
    m, s = divmod(abs(int(seconds)), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%m-%d  %H:%M")
    except Exception:
        return iso


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(ctk.CTk):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.title("番茄时钟")
        self.geometry("360x460")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # ── Mode selector ─────────────────────────────────────────────────────
        self._mode_var = ctk.StringVar(value="25 分钟")
        self._mode_seg = ctk.CTkSegmentedButton(
            self,
            values=["25 分钟", "自定义", "正计时"],
            variable=self._mode_var,
            command=self._on_mode_change,
            font=ctk.CTkFont(size=13),
            height=32,
        )
        self._mode_seg.grid(row=0, column=0, padx=20, pady=(20, 0), sticky="ew")

        # ── Timer display ─────────────────────────────────────────────────────
        self._time_label = ctk.CTkLabel(
            self,
            text="25:00",
            font=ctk.CTkFont(size=76, weight="bold"),
            text_color="white",
        )
        self._time_label.grid(row=1, column=0, pady=(30, 0))

        # ── Status label ──────────────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self,
            text="准备开始",
            font=ctk.CTkFont(size=13),
            text_color=TEXT_DIM,
        )
        self._status_label.grid(row=2, column=0, pady=(4, 0))

        # ── Control buttons ───────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=(28, 0), padx=20, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self._btn_start = ctk.CTkButton(
            btn_frame,
            text="▶  开始",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            command=self._on_start,
        )
        self._btn_start.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._btn_pause = ctk.CTkButton(
            btn_frame,
            text="⏸  暂停",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            font=ctk.CTkFont(size=14),
            height=44,
            state="disabled",
            command=self._on_pause,
        )
        self._btn_pause.grid(row=0, column=1, padx=3, sticky="ew")

        self._btn_stop = ctk.CTkButton(
            btn_frame,
            text="⏹",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            font=ctk.CTkFont(size=14),
            height=44,
            width=44,
            state="disabled",
            command=self._on_stop,
        )
        self._btn_stop.grid(row=0, column=2, padx=(6, 0))

        # ── Bottom action bar ─────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, pady=(24, 20), padx=20, sticky="ew")
        bottom.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            bottom,
            text="📋  历史记录",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            font=ctk.CTkFont(size=13),
            height=36,
            command=self._open_history,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            bottom,
            text="⚙  设置",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            font=ctk.CTkFont(size=13),
            height=36,
            command=self._open_settings,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # ── Note preview label ────────────────────────────────────────────────
        self._note_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
            wraplength=320,
        )
        self._note_label.grid(row=5, column=0, pady=(0, 10))

    # ── Timer callbacks (called from App, already scheduled on main thread) ───

    def update_display(self, elapsed: int, total: int, display_val: int):
        self._time_label.configure(text=fmt_time(display_val))

    def on_state_change(self, state: TimerState):
        if state == TimerState.RUNNING:
            self._btn_start.configure(state="disabled")
            self._btn_pause.configure(state="normal", text="⏸  暂停")
            self._btn_stop.configure(state="normal")
            self._status_label.configure(text="计时中…", text_color=ACCENT)
        elif state == TimerState.PAUSED:
            self._btn_pause.configure(text="▶  继续")
            self._status_label.configure(text="已暂停", text_color="#ddaa00")
        elif state == TimerState.IDLE:
            self._btn_start.configure(state="normal")
            self._btn_pause.configure(state="disabled", text="⏸  暂停")
            self._btn_stop.configure(state="disabled")
            self._status_label.configure(text="准备开始", text_color=TEXT_DIM)
            self._note_label.configure(text="")
            # Reset display
            timer = self.app.timer
            default = "25:00" if timer.mode != TimerMode.COUNTUP else "00:00"
            self._time_label.configure(text=default)
        elif state == TimerState.FINISHED:
            self._status_label.configure(text="完成！", text_color="#44bb44")

    def set_current_note(self, note: str):
        preview = note[:40] + ("…" if len(note) > 40 else "")
        self._note_label.configure(text=preview)

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_start(self):
        # Disable mode selector while running
        dialog = NoteDialog(self, self.app.db)
        self.wait_window(dialog)
        if dialog.confirmed:
            self.app.start_timer(note=dialog.note, tags=dialog.selected_tags)
            self.set_current_note(dialog.note)

    def _on_pause(self):
        self.app.timer.toggle_pause()

    def _on_stop(self):
        self.app.timer.stop()

    def _on_mode_change(self, label: str):
        mode = MODE_BY_LABEL.get(label, TimerMode.COUNTDOWN_25)
        custom_min = int(self.app.db.get_setting("custom_duration", "25"))
        self.app.timer.set_mode(mode, custom_min)
        if mode == TimerMode.COUNTDOWN_25:
            self._time_label.configure(text="25:00")
            self._btn_stop.configure(text="⏹")
        elif mode == TimerMode.COUNTDOWN_CUSTOM:
            self._time_label.configure(text=fmt_time(custom_min * 60))
            self._btn_stop.configure(text="⏹")
        else:
            self._time_label.configure(text="00:00")
            self._btn_stop.configure(text="✓ 完成")

    def _open_history(self):
        HistoryPanel(self, self.app)

    def _open_settings(self):
        SettingsDialog(self, self.app)

    def _on_close(self):
        self.withdraw()

    # ── Public helpers ────────────────────────────────────────────────────────

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()


# ── Note Dialog ───────────────────────────────────────────────────────────────

class NoteDialog(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.confirmed = False
        self.note = ""
        self.selected_tags: list[str] = []
        self._tag_vars: dict[str, ctk.BooleanVar] = {}

        self.title("开始番茄钟")
        self.geometry("380x440")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="这段时间你打算做什么？",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(24, 12), sticky="w")

        self._text = ctk.CTkTextbox(self, height=100, font=ctk.CTkFont(size=13))
        self._text.grid(row=1, column=0, padx=24, sticky="ew")
        self._text.focus_set()

        ctk.CTkLabel(
            self,
            text="标签",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=2, column=0, padx=24, pady=(16, 6), sticky="w")

        self._tag_frame = ctk.CTkScrollableFrame(self, height=100, fg_color="transparent")
        self._tag_frame.grid(row=3, column=0, padx=24, sticky="ew")
        self._reload_tags()

        ctk.CTkButton(
            self,
            text="+ 新标签",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._add_tag_dialog,
        ).grid(row=4, column=0, padx=24, pady=(8, 0), sticky="w")

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=5, column=0, padx=24, pady=(20, 24), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_row,
            text="取消",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            command=self._cancel,
        ).grid(row=0, column=0, padx=(0, 8), sticky="ew")

        ctk.CTkButton(
            btn_row,
            text="开始计时 ▶",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(weight="bold"),
            command=self._confirm,
        ).grid(row=0, column=1, padx=(8, 0), sticky="ew")

        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self._cancel())

    def _reload_tags(self):
        for w in self._tag_frame.winfo_children():
            w.destroy()
        self._tag_vars.clear()
        tags = self.db.get_tags()
        col = 0
        row = 0
        for i, tag in enumerate(tags):
            var = ctk.BooleanVar()
            self._tag_vars[tag["name"]] = var
            cb = ctk.CTkCheckBox(
                self._tag_frame,
                text=tag["name"],
                variable=var,
                font=ctk.CTkFont(size=12),
                checkbox_width=16,
                checkbox_height=16,
            )
            cb.grid(row=row, column=col, padx=6, pady=3, sticky="w")
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _add_tag_dialog(self):
        win = ctk.CTkToplevel(self)
        win.title("新标签")
        win.geometry("260x130")
        win.grab_set()
        entry = ctk.CTkEntry(win, placeholder_text="标签名称", width=200)
        entry.pack(padx=24, pady=(20, 8))
        entry.focus_set()

        def save():
            name = entry.get().strip()
            if name:
                self.db.add_tag(name)
                win.destroy()
                self._reload_tags()
            else:
                win.destroy()

        ctk.CTkButton(win, text="添加", command=save).pack()
        win.bind("<Return>", lambda e: save())

    def _confirm(self):
        self.note = self._text.get("1.0", "end").strip()
        self.selected_tags = [n for n, v in self._tag_vars.items() if v.get()]
        self.confirmed = True
        self.destroy()

    def _cancel(self):
        self.confirmed = False
        self.destroy()


# ── History Panel ─────────────────────────────────────────────────────────────

class HistoryPanel(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("历史记录")
        self.geometry("560x520")
        self.resizable(True, True)
        self._build()
        self._load()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top, text="历史记录", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            top,
            text="导出 .ics",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            width=90,
            height=30,
            font=ctk.CTkFont(size=12),
            command=self._export_ics,
        ).grid(row=0, column=1, padx=(8, 0))

        # ── Scrollable list ───────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        sessions = self.app.db.get_sessions(limit=200)
        if not sessions:
            ctk.CTkLabel(
                self._scroll,
                text="暂无记录",
                text_color=TEXT_DIM,
                font=ctk.CTkFont(size=13),
            ).grid(pady=40)
            return

        for i, s in enumerate(sessions):
            self._add_row(i, s)

    def _add_row(self, idx: int, s: dict):
        bg = "#1e1e2e" if idx % 2 == 0 else "#222233"
        card = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=8)
        card.grid(row=idx, column=0, pady=3, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        # Date / time
        ctk.CTkLabel(
            card,
            text=fmt_dt(s["start_time"]),
            font=ctk.CTkFont(size=11),
            text_color=TEXT_DIM,
            width=90,
        ).grid(row=0, column=0, padx=(10, 6), pady=(8, 0), sticky="nw")

        # Duration badge
        dur = s.get("actual_duration") or s.get("planned_duration") or 0
        dur_text = fmt_time(dur)
        mode_map = {"25min": "25m", "custom": "自定义", "countup": "正计时"}
        mode_text = mode_map.get(s.get("mode", ""), "")
        ctk.CTkLabel(
            card,
            text=f"{dur_text}  {mode_text}",
            font=ctk.CTkFont(size=11),
            text_color="#aaaacc",
        ).grid(row=0, column=2, padx=(4, 10), pady=(8, 0), sticky="ne")

        # Tags
        tags = s.get("tags", [])
        if tags:
            tag_str = "  ".join(f"#{t}" for t in tags)
            ctk.CTkLabel(
                card,
                text=tag_str,
                font=ctk.CTkFont(size=10),
                text_color=ACCENT,
            ).grid(row=1, column=1, padx=4, pady=(2, 0), sticky="w")

        # Note
        note = s.get("note", "")
        if note:
            ctk.CTkLabel(
                card,
                text=note,
                font=ctk.CTkFont(size=12),
                wraplength=340,
                justify="left",
            ).grid(row=2, column=0, columnspan=3, padx=10, pady=(2, 8), sticky="w")
        else:
            card.grid_rowconfigure(2, minsize=8)

    def _export_ics(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".ics",
            filetypes=[("iCalendar", "*.ics"), ("所有文件", "*.*")],
            initialfile="pomodoro_history.ics",
        )
        if not path:
            return
        try:
            from calendar_sync import export_ics_file
            sessions = self.app.db.get_all_sessions()
            export_ics_file(sessions, path)
            messagebox.showinfo("导出成功", f"已导出 {len(sessions)} 条记录到：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))


# ── Settings Dialog ───────────────────────────────────────────────────────────

class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.title("设置")
        self.geometry("420x560")
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="设置", font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        # ── Custom duration ───────────────────────────────────────────────────
        self._section("自定义时长", row=1)
        dur_row = ctk.CTkFrame(self, fg_color="transparent")
        dur_row.grid(row=2, column=0, padx=24, pady=(0, 4), sticky="ew")
        dur_row.grid_columnconfigure(0, weight=1)

        saved_dur = self.db.get_setting("custom_duration", "25")
        self._dur_var = ctk.StringVar(value=saved_dur)
        ctk.CTkEntry(
            dur_row, textvariable=self._dur_var, width=80, placeholder_text="分钟"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(dur_row, text="分钟", text_color=TEXT_DIM).grid(
            row=0, column=1, padx=(8, 0)
        )

        # ── Startup ───────────────────────────────────────────────────────────
        self._section("开机自启", row=3)
        startup_val = self.db.get_setting("startup_enabled", "false") == "true"
        self._startup_var = ctk.BooleanVar(value=startup_val)
        ctk.CTkSwitch(
            self,
            text="启动 Windows 时自动运行番茄时钟",
            variable=self._startup_var,
            font=ctk.CTkFont(size=13),
        ).grid(row=4, column=0, padx=24, pady=(0, 4), sticky="w")

        # ── Google Calendar ───────────────────────────────────────────────────
        self._section("Google Calendar", row=5)

        gcal_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        gcal_frame.grid(row=6, column=0, padx=24, pady=(0, 4), sticky="ew")
        gcal_frame.grid_columnconfigure(0, weight=1)

        from calendar_sync import has_credentials, GCAL_SETUP_INSTRUCTIONS, DATA_DIR
        self._gcal_instructions = GCAL_SETUP_INSTRUCTIONS

        status_text = "✅ credentials.json 已就绪" if has_credentials() else "❌ 未配置 credentials.json"
        ctk.CTkLabel(
            gcal_frame, text=status_text, font=ctk.CTkFont(size=12)
        ).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")

        ctk.CTkButton(
            gcal_frame,
            text="查看配置说明",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._show_gcal_instructions,
        ).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

        gcal_enabled = self.db.get_setting("gcal_enabled", "false") == "true"
        self._gcal_var = ctk.BooleanVar(value=gcal_enabled)
        ctk.CTkSwitch(
            gcal_frame,
            text="计时结束后自动同步到 Google Calendar",
            variable=self._gcal_var,
            font=ctk.CTkFont(size=12),
        ).grid(row=2, column=0, padx=12, pady=(4, 4), sticky="w")

        cal_id = self.db.get_setting("gcal_calendar_id", "primary")
        self._cal_id_var = ctk.StringVar(value=cal_id)
        id_row = ctk.CTkFrame(gcal_frame, fg_color="transparent")
        id_row.grid(row=3, column=0, padx=12, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(id_row, text="日历 ID：", font=ctk.CTkFont(size=12), text_color=TEXT_DIM).grid(
            row=0, column=0
        )
        ctk.CTkEntry(
            id_row, textvariable=self._cal_id_var, width=180, placeholder_text="primary"
        ).grid(row=0, column=1, padx=(6, 0))

        btn_row = ctk.CTkFrame(gcal_frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="w")

        ctk.CTkButton(
            btn_row,
            text="连接账户（OAuth）",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._connect_gcal,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row,
            text="发送测试事件",
            fg_color="#2b2b3b",
            hover_color="#3a3a4a",
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._send_test_event,
        ).grid(row=0, column=1)

        # ── Save button ───────────────────────────────────────────────────────
        ctk.CTkButton(
            self,
            text="保存",
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save,
        ).grid(row=7, column=0, padx=24, pady=(16, 24), sticky="ew")

    def _section(self, title: str, row: int):
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#aaaacc",
        ).grid(row=row, column=0, padx=24, pady=(12, 4), sticky="w")

    def _show_gcal_instructions(self):
        win = ctk.CTkToplevel(self)
        win.title("Google Calendar 配置说明")
        win.geometry("480x420")
        win.grab_set()
        tb = ctk.CTkTextbox(win, font=ctk.CTkFont(size=12), wrap="word")
        tb.pack(fill="both", expand=True, padx=16, pady=16)
        tb.insert("1.0", self._gcal_instructions)
        tb.configure(state="disabled")

    def _connect_gcal(self):
        def do_auth():
            try:
                from calendar_sync import get_gcal_service
                get_gcal_service()
                self.after(0, lambda: messagebox.showinfo("成功", "Google Calendar 账户连接成功！"))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("连接失败", err))

        threading.Thread(target=do_auth, daemon=True).start()

    def _send_test_event(self):
        cal_id = self._cal_id_var.get().strip() or "primary"

        def do_test():
            try:
                from calendar_sync import sync_session_to_gcal
                from datetime import datetime, timedelta
                now = datetime.now()
                session = {
                    "start_time": (now - timedelta(minutes=25)).isoformat(),
                    "end_time": now.isoformat(),
                    "planned_duration": 25 * 60,
                    "actual_duration": 25 * 60,
                    "mode": "25min",
                    "note": "测试事件 — 番茄时钟连通性测试",
                    "tags": ["测试"],
                    "completed": True,
                }
                event_id = sync_session_to_gcal(session, cal_id)
                self.after(0, lambda: messagebox.showinfo(
                    "测试成功 ✅",
                    f"已在 Google Calendar 创建测试事件！\n\n"
                    f"日历：{cal_id}\n"
                    f"时间：{now.strftime('%H:%M')} 往前 25 分钟\n"
                    f"事件 ID：{event_id}"
                ))
            except Exception as e:
                err = str(e)
                self.after(0, lambda: messagebox.showerror("测试失败 ❌", err))

        threading.Thread(target=do_test, daemon=True).start()

    def _save(self):
        # Custom duration
        try:
            dur = int(self._dur_var.get())
            if dur < 1:
                dur = 1
        except ValueError:
            dur = 25
        self.db.set_setting("custom_duration", str(dur))

        # Startup
        startup = self._startup_var.get()
        self.db.set_setting("startup_enabled", str(startup).lower())
        self.app.set_startup(startup)

        # Google Calendar
        self.db.set_setting("gcal_enabled", str(self._gcal_var.get()).lower())
        self.db.set_setting("gcal_calendar_id", self._cal_id_var.get().strip() or "primary")

        self.destroy()
        messagebox.showinfo("已保存", "设置已保存。")
