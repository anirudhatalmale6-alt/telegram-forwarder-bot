Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TELEGRAM BOT - AUTO SETUP" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$botDir = "C:\TelegramBot"

# Create bot directory
if (!(Test-Path $botDir)) { New-Item -ItemType Directory -Path $botDir | Out-Null }

# Check if Python is installed
$pythonExists = $false
try { python --version 2>$null; $pythonExists = $true } catch {}

if (-not $pythonExists) {
    Write-Host "Downloading Python..." -ForegroundColor Yellow
    $pyInstaller = "$env:TEMP\python_installer.exe"
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe" -OutFile $pyInstaller
    Write-Host "Installing Python (this takes a minute)..." -ForegroundColor Yellow
    Start-Process -Wait -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1"
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Remove-Item $pyInstaller -Force
    Write-Host "Python installed!" -ForegroundColor Green
} else {
    Write-Host "Python already installed." -ForegroundColor Green
}

# Download bot files
Write-Host "Downloading bot files..." -ForegroundColor Yellow
$zipPath = "$env:TEMP\bot.zip"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri "https://github.com/anirudhatalmale6-alt/telegram-forwarder-bot/archive/refs/heads/main.zip" -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\bot_extract" -Force
Copy-Item "$env:TEMP\bot_extract\telegram-forwarder-bot-main\*" $botDir -Recurse -Force
Remove-Item $zipPath -Force
Remove-Item "$env:TEMP\bot_extract" -Recurse -Force
Write-Host "Bot files downloaded!" -ForegroundColor Green

# Install Telethon
Write-Host "Installing Telethon..." -ForegroundColor Yellow
& python -m pip install telethon==1.37.0
Write-Host "Telethon installed!" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Bot is installed at: $botDir" -ForegroundColor White
Write-Host ""
Write-Host "Starting the bot now..." -ForegroundColor Yellow
Write-Host "You will need to enter your PHONE NUMBER" -ForegroundColor Red
Write-Host "and a VERIFICATION CODE from Telegram." -ForegroundColor Red
Write-Host ""

Set-Location $botDir
& python bot.py
