@echo off
chcp 65001 >nul
echo 启动前端 Vite 开发服务器...
echo.
cd /d "%~dp0frontend"
echo 当前目录: %cd%
echo.
npm run dev
pause