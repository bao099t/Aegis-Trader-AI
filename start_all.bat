@echo off
title Aegis Zenith Command Center (ALL-IN-ONE)
color 0a

echo ==========================================================
echo    AEGIS ZENITH TRADER ^| INSTITUTIONAL LAUNCHER
echo ==========================================================
echo.
echo [1] Initializing Core Infrastructure (FastAPI)...
start "Aegis API Gateway" cmd /k "uvicorn src.api.server:app --host 127.0.0.1 --port 8000"

echo [2] Waiting for Neural Engines to warm up...
timeout /t 5 >nul

echo [3] Launching Zenith Hybrid Worker (The Brain)...
echo [3] Launching Zenith Hybrid Worker (The Brain)...
:loop
start /wait "Aegis Worker (Active Trading)" cmd /c "python src/main.py"
echo [WARNING] Worker process crashed or closed. Restarting in 5 seconds...
timeout /t 5 >nul
goto loop

echo [4] Opening Sentinel Dashboard (The Face)...
start "" "e:\tool crawl\dashboard\index.html"

echo.
echo [SUCCESS] SYSTEM DEPLOYED.
echo    - API: http://localhost:8000
echo    - Dashboard: Local HTML File
echo    - Worker: Active in background window
echo.
echo DO NOT CLOSE THIS WINDOW or the background services will stop.
pause
