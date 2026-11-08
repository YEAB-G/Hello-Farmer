@echo off
title Hello Farmer - Network Auto-Config & Startup
echo =======================================================
echo   Hello Farmer - Dynamic Network IP Auto-Configurator
echo =======================================================
echo Detecting active network IP and configuring Asterisk...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\update_network_ip.ps1"
echo.
echo Starting Hello Farmer Docker containers...
docker compose up -d
if %ERRORLEVEL% EQU 0 (
    echo.
    echo =======================================================
    echo   [SUCCESS] Hello Farmer is live and ready!
    echo   - Web Dashboard: http://localhost:3000
    echo   - Backend Docs:  http://localhost:8000/docs
    echo =======================================================
) else (
    echo.
    echo =======================================================
    echo   [NOTICE] Make sure Docker Desktop is open and running!
    echo =======================================================
)
echo.
pause
