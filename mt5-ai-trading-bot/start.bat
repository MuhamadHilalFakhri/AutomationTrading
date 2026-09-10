@echo off
REM MT5 Automation Trading launcher (Windows)
cd /d D:\Projects\mt5-ai-trading-bot
set PYTHON=D:\HermesAgent\hermes-agent\venv\Scripts\python.exe

if "%1"=="--once" (
    %PYTHON% run_bot.py --once
    goto :eof
)
if "%1"=="--server" (
    %PYTHON% server\main.py
    goto :eof
)
if "%1"=="--loop" (
    %PYTHON% run_bot.py --loop 60
    goto :eof
)
if "%1"=="--backtest" (
    %PYTHON% backtest\run_backtest.py
    goto :eof
)

echo Usage: start.bat [--once ^| --loop ^| --server ^| --backtest]
