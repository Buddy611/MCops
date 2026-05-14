@echo off
setlocal
set "REPLY=N"

echo ⚠️ WARNING: This will PERMANENTLY remove MCOps and ALL server data!
set /p "REPLY=Are you sure you want to continue? (y/N): "

if /i not "%REPLY%"=="y" (
    echo Uninstall cancelled.
    exit /b 0
)

echo.
echo 🛡️ MCOps Panel – Windows Uninstaller
echo ═══════════════════════════════════

:: 1. Stop Minecraft servers (attempt to kill java processes started by mcops)
echo 🛑 Stopping all Minecraft servers...
:: We try to kill java processes. Note: This might kill other java apps too, 
:: but without a more complex process tracker, this is the safest 'clean slate' approach.
taskkill /F /FI "WINDOWTITLE eq mc_*" /T >nul 2>&1
taskkill /F /IM java.exe /FI "MEMUSAGE gt 500000" >nul 2>&1
echo ✅ Server processes handled.

:: 2. Remove directories
echo 🗑️ Deleting files and directories...

if exist venv (
    echo   - Removing Virtual Environment...
    rmdir /s /q venv
)

set "DIRS=instances plugin-pool templates backups global logs"
for %%d in (%DIRS%) do (
    if exist %%d (
        echo   - Removing %%d...
        rmdir /s /q %%d
    )
)

if exist .env (
    echo   - Removing .env...
    del .env
)

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║       MCOps Panel has been completely removed.           ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
pause
