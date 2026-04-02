#!/bin/bash

# Arkanis AI OS - Bootstrap Loader
# Versão: 3.1.2

echo "🚀 Iniciando Arkanis AI OS Installer..."

# Verificar Git
if ! command -v git &> /dev/null; then
  echo "📦 Git não encontrado. Instalando..."
  sudo apt update -qq && sudo apt install -y git -qq
fi

# Limpeza de pastas temporárias se existirem
if [ -d "Arkanis" ]; then
    echo "⚠️  Pasta 'Arkanis' já existe. Removendo para instalação limpa..."
    rm -rf Arkanis
fi

# Clonar projeto
git clone https://github.com/arkanis-agent/Arkanis.git

# Entrar no diretório do Kernel (V3)
if [ -d "Arkanis/V3" ]; then
    cd Arkanis/V3
    # Executar o instalador real com o terminal conectado
    bash install.sh
else
    echo "❌ Erro: Estrutura do repositório inválida. Pasta V3 não encontrada."
    exit 1
fi
