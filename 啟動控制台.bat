@echo off
chcp 65001 >nul
title AI Content Pipeline Console
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual env not found: .venv\Scripts\python.exe
    pause
    exit /b 1
)

echo Starting console... browser will open at http://localhost:8080
echo Close this window or press Ctrl+C to stop the server.
echo.

".venv\Scripts\python.exe" app.py

if errorlevel 1 (
    echo.
    echo [ERROR] app.py exited with an error. See messages above.
    pause
)
