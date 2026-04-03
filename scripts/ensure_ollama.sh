#!/bin/bash
# ---------------------------------------------------------
# ARKANIS V3 - OLLAMA SERVICE MANAGER (Portable)
# Checks and starts the local Ollama instance if needed.
# ---------------------------------------------------------

OLLAMA_URL="http://localhost:11434/api/tags"
OLLAMA_EXE=$(which ollama)

if [ -z "$OLLAMA_EXE" ]; then
    echo "❌ [OLLAMA] Not found in PATH. Please install it first: https://ollama.com"
    exit 1
fi

echo "🔍 [OLLAMA] Checking service status..."

# Check if responding - using -m (max-time) for portability
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$OLLAMA_URL" -m 2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ [OLLAMA] Service is already running and healthy."
    exit 0
fi

echo "⚠️  [OLLAMA] Service not responding (Status: $HTTP_CODE). Attempting to start..."

# 1. Try starting the service directly in background
echo "🚀 [OLLAMA] Starting service in background (ollama serve)..."
nohup ollama serve > /tmp/ollama_serve.log 2>&1 &

# 2. Wait up to 10s for initialization
for i in {1..10}; do
    sleep 1
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$OLLAMA_URL" -m 1)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ [OLLAMA] Service started successfully!"
        exit 0
    fi
    echo "   ...waiting ($i/10)"
done

echo "❌ [OLLAMA] Failed to start service automatically. Please run 'ollama serve' manually."
exit 1
