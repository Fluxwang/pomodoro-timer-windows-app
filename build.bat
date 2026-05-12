@echo off
chcp 65001 > nul
echo ========================================
echo  番茄时钟 Build Script
echo ========================================
echo.

echo [1/2] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Building .exe with PyInstaller...
pyinstaller pomodoro.spec --clean
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo  Output: dist\pomodoro.exe
echo ========================================
pause
