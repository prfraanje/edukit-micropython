#!/bin/bash
# Setup script for edukit-micropython on Linux/Mac
# This script creates a virtual environment and installs dependencies

set -e  # Exit on error

echo "========================================"
echo "edukit-micropython Setup Script"
echo "========================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3 using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Mac: brew install python3"
    exit 1
fi

echo "[1/4] Python found:"
python3 --version
echo ""

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "[2/4] Virtual environment already exists, skipping creation"
else
    echo "[2/4] Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created successfully"
fi
echo ""

# Activate virtual environment and install dependencies
echo "[3/4] Installing dependencies..."
echo "This may take a few minutes..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo ""

# Install mpy-cross for compiling MicroPython files
echo "[4/4] Installing mpy-cross compiler..."
pip install mpy-cross==1.24.0 || echo "WARNING: Failed to install mpy-cross. You can still use .py files."
echo ""

echo "========================================"
echo "Setup completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo "2. Run the application:"
echo "   python textual_mpy_edukit.py"
echo ""
echo "TIP: You need to activate the virtual environment every time"
echo "     you open a new terminal. Look for (venv) in your prompt."
echo ""
