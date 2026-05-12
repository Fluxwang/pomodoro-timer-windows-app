# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for 番茄时钟

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('customtkinter'),
    hiddenimports=[
        # customtkinter
        'customtkinter',
        # PIL / Pillow
        'PIL',
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ImageDraw',
        # pystray
        'pystray',
        'pystray._win32',
        # plyer notifications
        'plyer',
        'plyer.platforms',
        'plyer.platforms.win',
        'plyer.platforms.win.notification',
        # icalendar
        'icalendar',
        # Google API
        'googleapiclient',
        'googleapiclient.discovery',
        'google.oauth2',
        'google.oauth2.credentials',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'google_auth_httplib2',
        'google.auth.transport.requests',
        # Microsoft Graph / Outlook API
        'msal',
        'requests',
        # stdlib
        'sqlite3',
        'json',
        'threading',
        'subprocess',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pomodoro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/pomodoro.ico',
)
