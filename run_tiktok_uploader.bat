@echo off
REM Batch script to run TikTok Upload Manager

echo Starting TikTok Upload Manager...
python tiktok_uploader_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Failed to start TikTok Upload Manager
    echo Please make sure you have installed all required dependencies:
    echo pip install -r requirements.txt
    echo.
    pause
)
