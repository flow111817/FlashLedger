@echo off
title FlashLedger Launcher

echo ==============================================
echo       FlashLedger 一键启动脚本
echo ==============================================

:: 1. 启动后端 (PocketBase)
echo [1/2] 正在启动后端服务...

:: /k 表示执行完保留窗口，以便查看日志
start "FlashLedger Backend" cmd /k "cd pocketbase && pocketbase.exe serve"

:: 等待 1 秒，确保后端先跑起来
timeout /t 1 /nobreak >nul

:: 2. 启动前端 (Vue)
echo [2/2] 正在启动前端服务...
start "FlashLedger Frontend" cmd /k "cd flash-ledger-web && npm run dev"

echo.
echo ==============================================
echo  启动完成！请勿关闭弹出的两个黑色窗口。
echo  请在浏览器访问: http://localhost:5173
echo ==============================================
timeout /t 3 /nobreak >nul