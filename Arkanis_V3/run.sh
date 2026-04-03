#!/bin/bash
# Arkanis V3.1 — Inicializador principal
# Usa o ambiente virtual (venv) com Playwright e monitoring_tools

V3_DIR=$(dirname "$(readlink -f "$0")")
VENV_PYTHON="$V3_DIR/venv/bin/python3"

# Verificar se o venv existe
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Ambiente virtual não encontrado. Execute install.sh primeiro."
    exit 1
fi

echo "🚀 Iniciando Arkanis V3.1..."
echo "   Python: $VENV_PYTHON"
echo "   Porta:  http://localhost:8000"
echo ""

cd "$V3_DIR"
"$VENV_PYTHON" main.py --web
