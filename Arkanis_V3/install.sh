#!/bin/bash

# Arkanis AI OS - Deep Kernel Installer
# Versão: 3.4.0 - Virtual Environment Isolation (VENV)

BOLD=$(tput bold 2>/dev/null || echo "")
MAGENTA=$(tput setaf 5 2>/dev/null || echo "")
CYAN=$(tput setaf 6 2>/dev/null || echo "")
GREEN=$(tput setaf 2 2>/dev/null || echo "")
YELLOW=$(tput setaf 3 2>/dev/null || echo "")
NC=$(tput sgr0 2>/dev/null || echo "")

clear
echo -e "${MAGENTA}${BOLD}----------------------------------------------------------"
echo "  █████╗ ██████╗ ██╗  ██╗ █████╗ ███╗   ██╗██╗███████╗"
echo " ██╔══██╗██╔══██╗██║ ██╔╝██╔══██╗████╗  ██║██║██╔════╝"
echo " ███████║██████╔╝█████╔╝ ███████║██╔██╗ ██║██║███████╗"
echo " ██╔══██║██╔══██╗██╔═██╗ ██╔══██║██║╚██╗██║██║╚════██║"
echo " ██║  ██║██║  ██║██║  ██╗██║  ██║██║ ╚████║██║███████║"
echo " ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚══════╝"
echo -e "${NC}             ${CYAN}${BOLD}AI AGENT OPERATING SYSTEM${NC}"
echo -e "${MAGENTA}${BOLD}----------------------------------------------------------${NC}\n"

V3_DIR=$(dirname "$(readlink -f "$0")")

# 1. Limpeza de Legado
echo "🧹 Limpando processos antigos na porta 8000..."
sudo fuser -k 8000/tcp > /dev/null 2>&1 || true

# 2. Diagnóstico
echo "🔍 Analisando hardware..."
HW_JSON=$(python3 "$V3_DIR/scripts/hardware_detect.py" 2>/dev/null)
MODEL=$(echo $HW_JSON | grep -oP '"recommended_model": "\K[^"]+' || echo "llama3.2:3b")

# 3. Consentimento
printf "${CYAN}${BOLD}Deseja iniciar a instalação (Modo Venv) do Arkanis V3.1? (y/n): ${NC}"
exec 3< /dev/tty; read -u 3 confirm; exec 3<&-
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "❌ Cancelado."; exit 0
fi

# 4. Criação do Ambiente Virtual (CORREÇÃO CRÍTICA)
echo "📦 Criando 'casulo' isolado (Virtualenv)..."
python3 -m venv "$V3_DIR/.venv" || {
    echo "⚠️  ERRO: Seu sistema não tem python3-venv instalado."
    echo "Executando: sudo apt update && sudo apt install -y python3-venv"
    sudo apt update && sudo apt install -y python3-venv -y
    python3 -m venv "$V3_DIR/.venv"
}

# Usar os binários do Venv a partir de agora
VENV_PYTHON="$V3_DIR/.venv/bin/python3"
VENV_PIP="$V3_DIR/.venv/bin/pip"

echo "📦 Sincronizando bibliotecas do motor no ambiente isolado..."
$VENV_PIP install --upgrade pip --quiet
$VENV_PIP install -r "$V3_DIR/requirements.txt" --quiet
$VENV_PYTHON -m playwright install chromium --quiet > /dev/null 2>&1

# 5. Configuração
echo "⚙️  Configurando núcleos do sistema..."
cat <<EOF > "$V3_DIR/.env"
ARKANIS_MODE=local
ARKANIS_MODEL=$MODEL
SETUP_COMPLETE=true
EOF

# 6. Wrapper da CLI atualizado para usar o Venv
cat <<EOF > "$V3_DIR/arkanis_wrap.sh"
#!/bin/bash
cd "$V3_DIR"
"$VENV_PYTHON" "$V3_DIR/main.py" "\$@"
EOF
chmod +x "$V3_DIR/arkanis_wrap.sh"
sudo ln -sf "$V3_DIR/arkanis_wrap.sh" /usr/local/bin/arkanis 2>/dev/null

# 7. Boot Persistente
echo -e "\n${GREEN}✅ AMBIENTE ISOLADO CONFIGURADO!${NC}"
echo "🚀 Iniciando motor gráfico..."

LOG_FILE="$V3_DIR/arkanis_server.log"
nohup "$VENV_PYTHON" "$V3_DIR/main.py" --web > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

echo "⏳ Aguardando sincronização do servidor..."
for i in {1..12}; do
    if grep -q "http://localhost:8000" "$LOG_FILE" 2>/dev/null; then
        echo "✅ Servidor Online!"
        break
    fi
    sleep 1
    printf "."
done

# Abertura
echo -e "\n[Action] Performing first-run intelligence validation..."
"$VENV_PYTHON" "$V3_DIR/scripts/verify_intelligence.py"

( xdg-open "http://localhost:8000" || open "http://localhost:8000" ) >/dev/null 2>&1

echo -e "\n\n${BOLD}ARKANIS PRONTO!${NC}"
echo "Interface: http://localhost:8000"
echo "Logs: $LOG_FILE"
echo -e "\n${YELLOW}O terminal pode ser fechado. Arkanis está rodando no ambiente isolado.${NC}"
sleep 1
