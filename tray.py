import threading
from PIL import Image, ImageDraw


def _make_icon(state: str = "idle") -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = {
        "idle":    (130, 130, 130),
        "running": (220, 60,  50),
        "paused":  (210, 140, 30),
    }
    body_color = colors.get(state, colors["idle"])

    # Tomato body
    m = 8
    draw.ellipse([m, m + 6, size - m, size - m + 2], fill=body_color)

    # Stem
    draw.rectangle([size // 2 - 2, 3, size // 2 + 2, m + 4], fill=(50, 140, 50))

    # Leaf
    draw.polygon(
        [(size // 2, 5), (size // 2 + 12, 2), (size // 2 + 10, m + 4)],
        fill=(60, 160, 60),
    )
    return img


class SystemTray:
    def __init__(self, app):
        self.app = app
        self._icon = None
        self._current_state = "idle"

    def run(self):
        try:
            import pystray
        except ImportError:
            return

        menu = pystray.Menu(
            pystray.MenuItem("显示窗口", self._show, default=True),
            pystray.MenuItem("开始 25 分钟", self._quick_start),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit),
        )
        self._icon = pystray.Icon(
            "pomodoro",
            _make_icon("idle"),
            "Pomodoro",  # X11 WM_NAME requires ASCII; tooltip on Windows can differ
            menu,
        )
        self._icon.run()

    def set_state(self, state: str):
        """Update tray icon color. Call from any thread."""
        if self._icon is None or state == self._current_state:
            return
        self._current_state = state
        try:
            self._icon.icon = _make_icon(state)
        except Exception:
            pass

    def stop(self):
        if self._icon:
            self._icon.stop()

    # ── Menu callbacks (run in tray thread) ───────────────────────────────────

    def _show(self, icon, item):
        self.app.show_window()

    def _quick_start(self, icon, item):
        self.app.quick_start_25()

    def _quit(self, icon, item):
        self.app.quit()
