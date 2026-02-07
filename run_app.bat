@echo off
echo Starting Market Intelligence System...

:: Start API Server in a new window
start "Stock Alert API & Dashboard" cmd /k "uvicorn src.api.server:app --port 8000"

:: Start Worker in a new window
start "Stock Alert Worker" cmd /k "python src/main.py"

echo ==================================================
echo System is running!
echo Dashboard: http://localhost:8000
echo Messages will be sent to your Discord Webhook.
echo ==================================================
pause
