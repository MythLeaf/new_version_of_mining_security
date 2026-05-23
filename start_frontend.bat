@echo off
chcp 65001 >nul
echo Starting frontend Vite dev server on http://localhost:5173 ...
echo.
cd /d "%~dp0frontend"
echo Current directory: %cd%
echo.
npm.cmd run dev
pause
