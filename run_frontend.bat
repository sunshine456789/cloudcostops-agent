@echo off
chcp 65001 >nul

title CloudCostOps Frontend

cd /d "%~dp0frontend"

echo.
echo ============================================================
echo                  CloudCostOps Frontend
echo ============================================================
echo.

if not exist "package.json" (
    echo [ERROR] frontend\package.json not found.
    echo.
    echo Current directory:
    cd
    echo.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo [INFO] node_modules not found.
    echo [INFO] Running npm install...
    echo.

    call npm install

    if errorlevel 1 (
        echo.
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
)

echo [OK] Frontend environment ready.
echo.
echo Starting Vite...
echo.

call npm run dev -- --host 127.0.0.1 --port 5173

echo.
echo Frontend stopped.
pause