@echo off
echo ============================================
echo   TELEGRAM FORWARDER BOT - AUTO INSTALLER
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found. Downloading Python installer...
    echo.
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo Installing Python silently...
    %TEMP%\python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1
    echo Python installed. Please close this window and run install.bat again.
    pause
    exit /b
)

echo Python found:
python --version
echo.

echo Installing required packages...
pip install telethon==1.37.0
echo.

echo ============================================
echo   Installation complete!
echo ============================================
echo.
echo To start the bot, run: python bot.py
echo The first time, you will need to enter your
echo Telegram phone number and verification code.
echo.
echo After that, the bot runs automatically.
echo.
pause
