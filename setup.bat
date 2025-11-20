@echo off
REM Setup script for edukit-micropython on Windows
REM This script creates a virtual environment and installs dependencies

echo ========================================
echo edukit-micropython Setup Script
echo ========================================
echo.

REM Check if Python is installed
call python --version >null 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo here

echo [1/4] Python found:
call python --version
echo.

REM Check if virtual environment already exists
if exist "venv" (
    echo [2/4] Virtual environment already exists, skipping creation
) else (
    echo [2/4] Creating virtual environment...
    call python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)
echo.

REM Activate virtual environment and install dependencies
echo [3/4] Installing dependencies...
echo This may take a few minutes...
call venv\Scripts\activate.bat
call python -m pip install --upgrade pip
call pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

REM Install mpy-cross for compiling MicroPython files
echo [4/4] Installing mpy-cross compiler...
call pip install mpy-cross==1.24.0
if errorlevel 1 (
    echo WARNING: Failed to install mpy-cross
    echo You can still use .py files instead of compiled .mpy files
)
echo.

echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Close this window
echo 2. Open a NEW terminal/command prompt
echo 3. Navigate to this folder: cd %CD%
echo 4. Activate the virtual environment: venv\Scripts\activate
echo 5. Run the application: python textual_mpy_edukit.py
echo.
echo TIP: You need to activate the virtual environment every time
echo      you open a new terminal. Look for (venv) in your prompt.
echo.
pause
