@echo off
echo ======================================================================
echo   EventEngine - Complete System Startup
echo ======================================================================
echo.
echo   Starting both API Server and Autonomous Agent...
echo.
echo ======================================================================
echo.

REM Start API Server in a new window
start "EventEngine API Server" python run.py

REM Wait a bit for API to initialize
timeout /t 3 /nobreak >nul

REM Start Agent in a new window
start "EventEngine Agent" python scripts\run_agent.py

echo.
echo ======================================================================
echo   EventEngine System Running!
echo ======================================================================
echo.
echo   Two windows opened:
echo   1. API Server (Port 8000)
echo   2. Autonomous Agent (Background tasks)
echo.
echo   Frontend URL:
echo   -^> http://localhost:8000/frontend/login.html
echo.
echo   API Docs:
echo   -^> http://localhost:8000/docs
echo.
echo   Close both windows to stop the system.
echo ======================================================================
echo.
pause
