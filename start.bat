@echo off
setlocal
title Telegram Vault Launcher - DEBUG MODE
echo ==============================================
echo  Telegram Vault - DEBUG Launcher
echo ==============================================

echo [DEBUG] Step 1: Current directory: %CD%
echo [INFO] Press any key to continue...
pause

:: venv check
if exist venv\Scripts\activate.bat (
    echo [DEBUG] Step 2: venv found, activating...
    set "ACTIVATE_CMD=call venv\Scripts\activate.bat &"
) else (
    echo [DEBUG] Step 2: venv NOT FOUND! Attempting to use system Python.
    set "ACTIVATE_CMD="
)
pause

echo [DEBUG] Step 3: Python check...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python command is not working! 
    echo Please make sure Python is installed and added to PATH.
    pause
    exit /b
)
echo [OK] Python found.
pause

echo [DEBUG] Step 4: Starting FastAPI Server...
start "FastAPI Server" cmd /k "%ACTIVATE_CMD% python -m uvicorn app:app --host 0.0.0.0 --port 8000"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to open FastAPI window!
) else (
    echo [OK] FastAPI window triggered.
)
pause

echo [DEBUG] Step 5: Waiting (2 sec)...
timeout /t 2 /nobreak >nul

echo [DEBUG] Step 6: Starting Telegram Bot...
start "Telegram Bot" cmd /k "%ACTIVATE_CMD% python bot.py"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to open Bot window!
) else (
    echo [OK] Bot window triggered.
)
pause

echo.
echo ==============================================
echo [DEBUG] Launcher sequence completed. 
echo If the windows have opened, you can close this screen.
echo ==============================================
pause
