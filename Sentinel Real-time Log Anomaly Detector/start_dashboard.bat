@echo off
set PYTHONUNBUFFERED=1
echo Starting Sentinel Web Server...

:: Start the Flask server in a new command prompt window
start "Sentinel Web Server" cmd /k ".\.venv\Scripts\python web\app.py"

echo Waiting for the server to spin up...
timeout /t 3 /nobreak >nul

:: Automatically open the default web browser to the correct link
echo Opening dashboard in your browser...
start http://127.0.0.1:5000
