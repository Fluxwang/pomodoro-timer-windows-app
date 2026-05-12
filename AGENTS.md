# Repository Guidelines

## Project Structure & Module Organization

This is a small Python desktop Pomodoro application with modules kept at the repository root.

- `main.py` is the application entry point and controller.
- `ui.py` contains the CustomTkinter UI.
- `timer.py` owns timer state, modes, and session timing behavior.
- `db.py` handles local persistence.
- `tray.py` and `notifier.py` provide system tray and desktop notification support.
- `calendar_sync.py` integrates completed sessions with Google Calendar.
- `pomodoro.spec` and `build.bat` define the Windows PyInstaller build.
- Runtime data, credentials, build outputs, virtualenvs, and caches are ignored by `.gitignore`.

There is currently no dedicated `tests/` directory. Add tests there when introducing automated coverage.

## Build, Test, and Development Commands

Create and activate a virtual environment before installing dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the app locally:

```bash
python main.py
```

Build the Windows executable:

```bat
build.bat
```

`build.bat` installs dependencies and runs `pyinstaller pomodoro.spec --clean`, producing `dist\pomodoro.exe`.

## Coding Style & Naming Conventions

Use Python 3 style with 4-space indentation, clear type hints for public methods, and short docstrings for modules or non-obvious functions. Follow the existing naming pattern: `snake_case` for functions and variables, `PascalCase` for classes, and enum-style names for timer modes and states.

Keep UI code in `ui.py`, persistence in `db.py`, and timer logic in `timer.py`. Avoid mixing blocking I/O into UI callbacks; use background threads as shown in `main.py` for calendar sync and tray work.

## Testing Guidelines

No test framework is configured yet. Prefer `pytest` for new tests and place files under `tests/` using names like `test_timer.py` or `test_db.py`.

Focus coverage on timer state transitions, session persistence, and Google Calendar sync error handling. For UI changes, add focused unit tests where possible and manually verify `python main.py` on the target platform.

## Commit & Pull Request Guidelines

The current Git history uses short Chinese commit messages such as `修复Oauth 按钮报错` and `添加日历测试功能，修复正计时无法提交bug`. Keep commits concise, imperative, and scoped to one logical change.

Pull requests should include a brief summary, test or manual verification steps, linked issues when applicable, and screenshots or screen recordings for visible UI changes. Do not commit generated folders such as `build/`, `dist/`, `__pycache__/`, local databases, Google credentials, or tokens.

## Security & Configuration Tips

Never commit `credentials.json`, `token.json`, SQLite databases, or files from `~/.pomodoro/`. Treat Google OAuth files and local session history as private user data.
