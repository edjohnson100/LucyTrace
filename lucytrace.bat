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

REM Check for venv
IF EXIST venv (
    echo Activating virtual environment...
    call venv\Scripts\activate
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