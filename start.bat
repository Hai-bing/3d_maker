@echo off
chcp 65001 >nul
title 3D Maker - 启动中...

:: ── 可配置路径 ──────────────────────────────
:: ComfyUI 安装目录：改成你自己的路径，或设置环境变量 COMFYUI_DIR
if not defined COMFYUI_DIR set "COMFYUI_DIR=C:\path\to\ComfyUI"

:: 项目根目录：按本脚本所在位置自动检测，无需修改
set "PROJECT_DIR=%~dp0"

echo ============================================
echo   3D Maker 平台启动
echo ============================================
echo.

:: ── 1. ComfyUI ──────────────────────────────
echo [1/2] 启动 ComfyUI (端口 8188)...
if not exist "%COMFYUI_DIR%\main.py" (
    echo    [错误] 找不到 ComfyUI：%COMFYUI_DIR%
    echo    请设置环境变量 COMFYUI_DIR 为 ComfyUI 安装目录，或修改本脚本第 8 行默认路径。
    echo    跳过 ComfyUI，继续启动 Flask ...
    goto flask_start
)
start "ComfyUI-SDXL" /D "%COMFYUI_DIR%" /MIN cmd /c "python main.py --port 8188"

:: 等待 ComfyUI 就绪
echo    等待 ComfyUI 就绪...
:wait_comfy
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8188/system_stats >nul 2>&1
if errorlevel 1 goto wait_comfy
echo    ComfyUI 已就绪 ✓

:: ── 2. Flask ────────────────────────────────
:flask_start
echo [2/2] 启动 Flask 后端 (端口 5000)...
start "3D-Maker-Flask" /D "%PROJECT_DIR%platform" /MIN cmd /c "seed3D_env\Scripts\python.exe backend\app.py"

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
