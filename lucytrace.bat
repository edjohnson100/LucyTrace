@echo off
REM LucyTrace: Turn "Ruff Drafts" into the "Director's Cut"
cd /d %~dp0

REM Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed.
    pause
    exit /b 1
)

REM Check for venv (checks venv_win, venv, or .venv)
IF EXIST venv_win\Scripts\activate.bat (
    echo Activating virtual environment: venv_win...
    call venv_win\Scripts\activate.bat
) ELSE IF EXIST venv\Scripts\activate.bat (
    echo Activating virtual environment: venv...
    call venv\Scripts\activate.bat
) ELSE IF EXIST .venv\Scripts\activate.bat (
    echo Activating virtual environment: .venv...
    call .venv\Scripts\activate.bat
)

REM If arguments were passed, forward directly to Python
IF NOT "%~1"=="" (
    python lucytrace.py %*
    exit /b %ERRORLEVEL%
)

REM --- Interactive Menu ---
echo.
echo ==========================================
echo   LUCYTRACE
echo   Turn "Ruff Drafts" into the "Director's Cut"
echo ==========================================
echo.
echo Select Processing Profile:
echo.
echo   [1] BASE (Fast)
echo       - Simple thresholding. 
echo       - Best for clean black ^& white line art.
echo.
echo   [2] ADVANCED (Smart)
echo       - Auto-levels, saturation detection.
echo       - Best for photos, gray scans, or comics.
echo.
set /p choice="Enter choice (1 or 2): "

IF "%choice%"=="1" (
    set ARGS=--profile base
) ELSE (
    set ARGS=--profile adv
)

echo.
echo Running LucyTrace with %ARGS%...
echo.

REM Run Python
python lucytrace.py %ARGS%

echo.
echo Processing complete. Press any key to exit...
pause >nul