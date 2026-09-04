@echo off
REM ============================================================
REM  Build "AI Trading Bot.exe" — GUI launcher all-in-one
REM  Icon: assets\icon.ico (dari D:\Logo.png)
REM  Output: "AI Trading Bot.exe" di folder project (sebelah config.yaml)
REM ============================================================
cd /d D:\Projects\mt5-ai-trading-bot
set PYTHON=D:\HermesAgent\hermes-agent\venv\Scripts\python.exe

%PYTHON% -m PyInstaller --onefile --windowed --clean --noconfirm ^
  --name "AI Trading Bot" ^
  --icon "assets\icon.ico" ^
  --add-data "assets;assets" ^
  --distpath . --workpath build --specpath build ^
  --paths server ^
  --hidden-import config --hidden-import mt5_gateway --hidden-import engine ^
  --hidden-import notifier --hidden-import risk_guard --hidden-import trade_manager ^
  --hidden-import logger_setup --hidden-import ai.agent --hidden-import ai.chart_renderer ^
  --hidden-import ai.prompts ^
  --collect-all MetaTrader5 ^
  --collect-submodules matplotlib ^
  gui_app.py

echo.
if exist "AI Trading Bot.exe" (
    del /q MT5TradingBot.exe 2>nul
    echo BUILD OK: %cd%\AI Trading Bot.exe
) else (
    echo BUILD GAGAL - cek output di atas
)
