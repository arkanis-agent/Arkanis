#!/bin/bash
# Testador de Lógica do Instalador

echo "--- TESTANDO INTERATIVIDADE ---"

# Função que vamos usar no install.sh
ask_user() {
    local prompt="$1"
    local choice
    printf "$prompt"
    # Tenta ler do terminal (/dev/tty) mas cai para stdin normal se falhar
    if [ -t 0 ]; then
        read -r choice
    else
        read -r choice < /dev/tty 2>/dev/null || read -r choice
    fi
    echo "$choice"
}

# Simulação de fluxo
echo "🔍 Simulando Hardware Scan..."
echo "✅ Encontrado: 8GB RAM | Tier: MID"

echo -e "\n--- PLANO DE INSTALAÇÃO ---"
echo "🚀 Passo 1: Cleanup"
echo "🧠 Passo 2: AI Engine"

RESPONSE=$(ask_user "Deseja continuar? (y/n): ")

if [[ "$RESPONSE" == "y" || "$RESPONSE" == "Y" ]]; then
    echo "RESULTADO: O Script continuaria a instalação."
else
    echo "RESULTADO: O Script pararia aqui com segurança."
fi
