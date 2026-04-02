#!/bin/bash

# ARKANIS V3.1 - WHISPER.CPP INSTALLER
# This script installs whisper.cpp into the V3/libs directory and downloads the base model.
# Requirements: git, make, g++, ffmpeg

set -e

# Define paths
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
V3_DIR=$(dirname "$SCRIPT_DIR")
LIBS_DIR="$V3_DIR/libs"
WHISPER_DIR="$LIBS_DIR/whisper.cpp"

echo "=== [ARKANIS] Whisper.cpp Setup ==="

# Create libs dir if missing
mkdir -p "$LIBS_DIR"

if [ ! -d "$WHISPER_DIR" ]; then
    echo "[1/3] Cloning whisper.cpp repository..."
    git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
else
    echo "[1/3] whisper.cpp already cloned."
fi

echo "[2/3] Building whisper.cpp binary with parallel jobs..."
mkdir -p "$WHISPER_DIR/build"
cd "$WHISPER_DIR/build"
cmake ..
make -j$(nproc)
cd "$WHISPER_DIR"

echo "[3/3] Downloading 'base' model..."
bash ./models/download-ggml-model.sh base

echo "=== [ARKANIS] Setup Complete! ==="
echo "Binary location: $WHISPER_DIR/build/bin/whisper-cli"
echo "Model location: $WHISPER_DIR/models/ggml-base.bin"
