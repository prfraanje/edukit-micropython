@echo off
REM Quick run script for edukit-micropython on Windows
REM This activates the virtual environment and runs the application

if not exist "venv" (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create the virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting edukit-micropython application...
python textual_mpy_edukit.py

REM Keep window open if there was an error
if errorlevel 1 pause
