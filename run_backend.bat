@echo off
chcp 65001 >nul

title CloudCostOps Backend

cd /d "%~dp0"

echo.
echo ============================================================
echo                  CloudCostOps Backend
echo ============================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    echo.
    echo Expected:
    echo %~dp0.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo [OK] Python environment found.
echo.
echo Starting FastAPI...
echo.

".venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

echo.
echo Backend stopped.
pause