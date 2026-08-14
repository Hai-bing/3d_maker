@echo off
chcp 65001 >nul
title 3D Maker - 启动中...

echo ============================================
echo   3D Maker 平台启动
echo ============================================
echo.

:: ── 1. ComfyUI ──────────────────────────────
echo [1/2] 启动 ComfyUI (端口 8188)...
start "ComfyUI-SDXL" /MIN cmd /c "cd /d C:\Users\Haibing\ComfyUI && python main.py --port 8188"

:: 等待 ComfyUI 就绪
echo    等待 ComfyUI 就绪...
:wait_comfy
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8188/system_stats >nul 2>&1
if errorlevel 1 goto wait_comfy
echo    ComfyUI 已就绪 ✓

:: ── 2. Flask ────────────────────────────────
echo [2/2] 启动 Flask 后端 (端口 5000)...
cd /d D:\3d_maker\platform
start "3D-Maker-Flask" /MIN cmd /c "seed3D_env\Scripts\python.exe backend\app.py"

:: 等待 Flask 就绪
echo    等待 Flask 就绪...
:wait_flask
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:5000/api/health >nul 2>&1
if errorlevel 1 goto wait_flask
echo    Flask 已就绪 ✓

:: ── 完成 ────────────────────────────────────
echo.
echo ============================================
echo   启动完成！浏览器打开:
echo   http://localhost:5000
echo ============================================
echo.
echo 关闭此窗口不会影响运行中的服务。
echo 要停止服务，请关闭 ComfyUI 和 Flask 窗口。
pause
