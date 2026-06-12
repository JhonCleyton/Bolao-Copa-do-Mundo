@echo off
echo ==========================================
echo    BOLAO COPA 2026 - Startup Script
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements if needed
echo Checking dependencies...
pip install -q -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Creating from .env.example...
    copy .env.example .env
    echo Please edit .env with your configuration before continuing.
    echo.
    pause
    exit
)

REM Start the application
echo.
echo ==========================================
echo    Starting Bolao Copa 2026...
echo ==========================================
echo.
echo Access the application at:
echo   - Website: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.

python main.py

pause
