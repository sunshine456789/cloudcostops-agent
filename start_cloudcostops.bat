@echo off
chcp 65001 >nul
setlocal

title CloudCostOps Pro Launcher

cd /d "%~dp0"

echo.
echo ============================================================
echo             CloudCostOps Pro AI FinOps Platform
echo ============================================================
echo.

REM ============================================================
REM Basic checks
REM ============================================================

echo [CHECK] Checking project environment...

if not exist "%~dp0run_backend.bat" (
    echo [ERROR] run_backend.bat not found.
    pause
    exit /b 1
)

if not exist "%~dp0run_frontend.bat" (
    echo [ERROR] run_frontend.bat not found.
    pause
    exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    pause
    exit /b 1
)

if not exist "%~dp0frontend\package.json" (
    echo [ERROR] frontend\package.json not found.
    pause
    exit /b 1
)

echo [OK] Project environment ready.
echo.

REM ============================================================
REM Start Backend
REM ============================================================

echo [1/4] Starting FastAPI backend...

start "CloudCostOps Backend" cmd /k call "%~dp0run_backend.bat"

echo Waiting for backend...

set /a BACKEND_RETRY=0

:WAIT_BACKEND

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/health' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if %ERRORLEVEL% EQU 0 goto BACKEND_READY

set /a BACKEND_RETRY+=1

if %BACKEND_RETRY% GEQ 30 goto BACKEND_FAILED

timeout /t 1 /nobreak >nul

goto WAIT_BACKEND


:BACKEND_READY

echo [OK] FastAPI backend is online.
echo.

REM ============================================================
REM Start Frontend
REM ============================================================

echo [2/4] Starting React frontend...

start "CloudCostOps Frontend" cmd /k call "%~dp0run_frontend.bat"

echo Waiting for frontend...

set /a FRONTEND_RETRY=0

:WAIT_FRONTEND

powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5173' -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }"

if %ERRORLEVEL% EQU 0 goto FRONTEND_READY

set /a FRONTEND_RETRY+=1

if %FRONTEND_RETRY% GEQ 40 goto FRONTEND_FAILED

timeout /t 1 /nobreak >nul

goto WAIT_FRONTEND


:FRONTEND_READY

echo [OK] React frontend is online.
echo.

REM ============================================================
REM Open browser
REM ============================================================

echo [3/4] Opening CloudCostOps frontend...

start "" "http://127.0.0.1:5173"

timeout /t 2 /nobreak >nul

echo [4/4] Opening FastAPI Swagger...

start "" "http://127.0.0.1:8000/docs"

echo.
echo ============================================================
echo                 CloudCostOps Pro READY
echo ============================================================
echo.
echo Frontend:
echo http://127.0.0.1:5173
echo.
echo Backend:
echo http://127.0.0.1:8000
echo.
echo Swagger:
echo http://127.0.0.1:8000/docs
echo.
echo Backend and Frontend are running
echo in separate terminal windows.
echo.
echo IMPORTANT:
echo Do not close Backend or Frontend windows while using the app.
echo.
echo ============================================================
echo.

pause
exit /b 0


REM ============================================================
REM Error handlers
REM ============================================================

:BACKEND_FAILED

echo.
echo ============================================================
echo [ERROR] FastAPI backend failed to start.
echo ============================================================
echo.
echo Please check the window:
echo CloudCostOps Backend
echo.
pause
exit /b 1


:FRONTEND_FAILED

echo.
echo ============================================================
echo [ERROR] React frontend failed to start.
echo ============================================================
echo.
echo Please check the window:
echo CloudCostOps Frontend
echo.
pause
exit /b 1