import os
import time
import shutil

# Arkanis Root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_TOOLS = os.path.join(ROOT, "tools", "network_tools.py")
NETWORK_TOOLS_BACKUP = NETWORK_TOOLS + ".broken"

def simulate():
    print("🔥 [CAOS] Iniciando simulação de falha catastrófica...")
    
    if os.path.exists(NETWORK_TOOLS):
        print(f"🧨 Removendo acesso ao módulo: {NETWORK_TOOLS}")
        shutil.move(NETWORK_TOOLS, NETWORK_TOOLS_BACKUP)
        print("✅ Módulo renomeado para .broken")
    else:
        print("⚠️ Módulo já está quebrado ou não encontrado.")

    print("\n👉 Agora, peça ao Arkanis: 'Minha internet não funciona, o que aconteceu?'")
    print("O Sentinel deve detectar o arquivo .broken e restaurá-lo.")

if __name__ == "__main__":
    simulate()
