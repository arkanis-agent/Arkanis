#!/bin/bash
# Arkanis Elite Setup Wizard

set -e

echo "=================================================="
echo "    ARKANIS V3.1 — ONE-STEP SETUP WIZARD          "
echo "=================================================="
echo ""

echo "[*] Verificando versão do Python..."
if ! command -v python3 &> /dev/null; then
    echo "[!] Python3 não encontrado. Instale o Python3 para continuar."
    exit 1
fi

echo "[*] Configurando Ambiente Virtual (.venv)..."
python3 -m venv .venv
source .venv/bin/activate

echo "[*] Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[*] Preparando estrutura de diretórios e arquivos..."
mkdir -p data logs db

# Cria configs dummy se não existirem
if [ ! -f "config/providers.json" ]; then
    echo '{"providers": {}, "models": []}' > config/providers.json
fi

if [ ! -f ".env" ]; then
    echo "Gerando chave de agente segura..."
    KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    echo "AGENT_KEY=$KEY" > .env
    echo "OPENROUTER_API_KEY=" >> .env
    echo "ANTHROPIC_API_KEY=" >> .env
    echo "[*] Arquivo .env gerado com sucesso."
fi

# Concede executabilidade 
if [ -f "arkanis" ]; then
    chmod +x arkanis
fi

echo ""
echo "=================================================="
echo " [SUCCESS] Arkanis V3.1 foi instalado com sucesso!"
echo " Para iniciar o sistema, digite:"
echo "     ./arkanis start"
echo "=================================================="
