#!/bin/bash

echo "🚀 Instalando Arkanis..."

# Instalar git se não tiver
if ! command -v git &> /dev/null; then
  echo "📦 Instalando git..."
  sudo apt update && sudo apt install -y git
fi

# Clonar projeto
git clone https://github.com/arkanis-agent/Arkanis.git

cd Arkanis

# Rodar instalador
sudo bash install.sh
