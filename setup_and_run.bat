@echo off
REM Cross-platform setup and run script for BitTorrent Backend (Windows)
REM This batch file calls the Python script

echo 🚀 BitTorrent Backend Setup ^& Run Script
echo ==================================================

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Run the Python setup script
python setup_and_run.py

pause
