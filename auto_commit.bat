@echo off
rem Auto-commit & push untuk repo AutomationTrading.
rem Dipanggil oleh agen AI (Hermes) setelah selesai mengubah file di repo ini.
rem Sebelumnya "wajib auto commit" diaktifkan oleh user (4 Sep 2026).

setlocal
cd /d "%~dp0"

rem Skip jika tidak ada perubahan
git status --porcelain >nul 2>&1
if errorlevel 1 (
  echo [auto-commit] bukan git repo, skip
  exit /b 0
)
git status --porcelain | findstr /r "." >nul
if errorlevel 1 (
  echo [auto-commit] tidak ada perubahan, skip
  exit /b 0
)

rem Cek konflik branch
git diff --name-only --diff-filter=U | findstr /r "." >nul
if not errorlevel 1 (
  echo [auto-commit] ada konflik merge, SKIP otomatis
  exit /b 1
)

set MSG=auto: %date% %time% - update
git add -A
git commit -m "%MSG%" >nul 2>&1
if errorlevel 1 (
  echo [auto-commit] commit gagal / tidak ada perubahan
  exit /b 1
)
echo [auto-commit] committed: %MSG%

rem Push
git push origin HEAD 2>&1 | findstr /v "warning: LF will be replaced" >nul
echo [auto-commit] pushed
exit /b 0