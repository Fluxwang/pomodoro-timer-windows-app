import sqlite3
import os
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.expanduser("~"), ".pomodoro")
DB_PATH = os.path.join(DATA_DIR, "pomodoro.db")


class Database:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time       TEXT NOT NULL,
                end_time         TEXT,
                planned_duration INTEGER,
                actual_duration  INTEGER,
                mode             TEXT NOT NULL,
                note             TEXT DEFAULT '',
                tags             TEXT DEFAULT '[]',
                completed        INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tags (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                name  TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#e94560'
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );

            INSERT OR IGNORE INTO tags (name) VALUES
                ('工作'), ('学习'), ('阅读'), ('编程'), ('写作');

            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('custom_duration', '25'),
                ('startup_enabled', 'false'),
                ('gcal_enabled',    'false'),
                ('gcal_calendar_id','primary');
        """)
        self.conn.commit()

    # ── Sessions ──────────────────────────────────────────────────────────────

    def save_session(self, data: dict) -> int:
        cur = self.conn.execute(
            """INSERT INTO sessions
               (start_time, end_time, planned_duration, actual_duration,
                mode, note, tags, completed)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                data.get("start_time"),
                data.get("end_time"),
                data.get("planned_duration"),
                data.get("actual_duration"),
                data.get("mode"),
                data.get("note", ""),
                json.dumps(data.get("tags", []), ensure_ascii=False),
                1 if data.get("completed") else 0,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_sessions(self, limit=100, offset=0, start_date=None, end_date=None):
        where = ""
        params = []
        if start_date:
            where += " AND start_time >= ?"
            params.append(start_date)
        if end_date:
            where += " AND start_time <= ?"
            params.append(end_date)
        params += [limit, offset]
        rows = self.conn.execute(
            f"""SELECT id, start_time, end_time, planned_duration, actual_duration,
                       mode, note, tags, completed
                FROM sessions WHERE 1=1 {where}
                ORDER BY start_time DESC LIMIT ? OFFSET ?""",
            params,
        ).fetchall()
        return [
            {
                "id": r[0],
                "start_time": r[1],
                "end_time": r[2],
                "planned_duration": r[3],
                "actual_duration": r[4],
                "mode": r[5],
                "note": r[6] or "",
                "tags": json.loads(r[7] or "[]"),
                "completed": bool(r[8]),
            }
            for r in rows
        ]

    def get_all_sessions(self):
        return self.get_sessions(limit=100000)

    # ── Tags ──────────────────────────────────────────────────────────────────

    def get_tags(self):
        rows = self.conn.execute(
            "SELECT id, name, color FROM tags ORDER BY name"
        ).fetchall()
        return [{"id": r[0], "name": r[1], "color": r[2]} for r in rows]

    def add_tag(self, name: str) -> bool:
        try:
            self.conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
            (key, str(value)),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
