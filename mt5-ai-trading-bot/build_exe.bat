@echo off
REM ============================================================
REM  Build "Automation Trading.exe" — GUI launcher all-in-one
REM  Icon: assets\LogoAT.ico
REM  Output: "Automation Trading.exe" di folder project (sebelah config.yaml)
REM ============================================================
cd /d D:\Projects\mt5-ai-trading-bot
set PYTHON=D:\HermesAgent\hermes-agent\venv\Scripts\python.exe

%PYTHON% -m PyInstaller --onefile --windowed --clean --noconfirm ^
  --name "Automation Trading" ^
  --icon "assets\LogoAT.ico" ^
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
if exist "Automation Trading.exe" (
    del /q MT5TradingBot.exe 2>nul
    echo BUILD OK: %cd%\Automation Trading.exe
) else (
    echo BUILD GAGAL - cek output di atas
)
