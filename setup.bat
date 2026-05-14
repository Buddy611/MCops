@echo off
setlocal

echo 🛡️ MCOps Panel – Windows Setup
echo ═══════════════════════════════

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.11 or newer.
    exit /b 1
)

:: Create virtual environment
if not exist venv (
    echo 📦 Creating Virtual Environment...
    python -m venv venv
)

:: Install dependencies
echo 📥 Installing dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" jinja2 cachetools python-multipart websockets aiofiles httpx

:: Create directories
echo 📁 Creating directory structure...
if not exist instances mkdir instances
if not exist plugin-pool mkdir plugin-pool
if not exist templates mkdir templates
if not exist backups mkdir backups
if not exist global mkdir global
if not exist logs mkdir logs

:: Generate random API key if not set
set "KEY_FILE=.env"
if not exist %KEY_FILE% (
    echo 🔑 Generating API Key...
    set /p "API_KEY=Enter your desired API Key (or press enter for a random one): "
    if "%API_KEY%"=="" (
        :: Simple random string for Windows
        set "API_KEY=%RANDOM%%RANDOM%%RANDOM%%RANDOM%"
    )
    echo MCOPS_API_KEY=%API_KEY% > %KEY_FILE%
    echo MCOPS_PORT=8000 >> %KEY_FILE%
    echo ✅ .env file created.
)

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║       MCOps Panel ready for Windows!                     ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo To start the panel, run:
echo   call venv\Scripts\activate
echo   set MCOPS_API_KEY=your_key_from_env
echo   python mcops\main.py
echo.
pause
