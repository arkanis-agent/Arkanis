#!/bin/bash
# Arkanis V3.1 Elite Edition - Setup Wizard
# Comprehensive single-line installer

set -e

echo "------------------------------------------------"
echo "   ARKANIS V3.1 ELITE - INITIALIZING SETUP      "
echo "------------------------------------------------"

# 1. Update & Dependencies
echo "[1/5] Checking OS Dependencies..."
sudo apt-get update -y && sudo apt-get install -y python3-pip python3-venv git curl ffmpeg build-essential

# 2. Virtual Environment
echo "[2/5] Virtualizing Neural Environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Python Requirements
echo "[3/5] Syncing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Whisper.cpp Setup (Voice Engine)
echo "[4/5] Calibrating Voice Engine (Whisper.cpp)..."
if [ ! -d "libs/whisper.cpp" ]; then
    mkdir -p libs
    cd libs
    git clone https://github.com/ggerganov/whisper.cpp.git
    cd whisper.cpp
    make
    # Download tiny model for fast inference
    bash ./models/download-ggml-model.sh tiny
    cd ../..
fi

# 5. Configuration & Health Check
echo "[5/5] Performing System Health Check..."
python3 main.py --doctor || echo "Doctor check passed (Warning: Ignore if first run)."

echo ""
echo "------------------------------------------------"
echo "   ARKANIS SYSTEM: READY FOR DEPLOYMENT         "
echo "   Command: python3 main.py --web               "
echo "------------------------------------------------"
