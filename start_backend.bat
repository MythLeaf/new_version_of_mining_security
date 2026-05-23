@echo off
chcp 65001 >nul
cd /d "%~dp0"
set MRA_ALLOW_UNAUTHENTICATED_ADMIN=true
set MRA_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
echo Starting backend API on http://localhost:8000 ...
"%~dp0..\mining_risk_agent\venv\Scripts\python.exe" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
pause
