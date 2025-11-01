#!/bin/bash
# Quick run script for edukit-micropython on Linux/Mac
# This activates the virtual environment and runs the application

if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup.sh first to create the virtual environment"
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting edukit-micropython application..."
python textual_mpy_edukit.py
