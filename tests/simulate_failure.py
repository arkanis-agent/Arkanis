import os
import time
import shutil
import stat

# Arkanis Root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_TOOLS = os.path.join(ROOT, "tools", "network_tools.py")
NETWORK_TOOLS_BACKUP = NETWORK_TOOLS + ".broken"

def check_safe_to_modify(filepath):
    """Verifica se podemos modificar o arquivo com segurança"""
    try:
        if not os.path.exists(filepath):
            return False
        if not os.access(filepath, os.W_OK):
            print(f"⚠️ Sem permissões de escrita em: {filepath}")
            return False
        return True
    except Exception as e:
        print(f"🚨 Erro ao verificar arquivo: {str(e)}")
        return False

def simulate():
    print("🔥 [CAOS] Iniciando simulação de falha catastrófica...")
    
    if check_safe_to_modify(NETWORK_TOOLS):
        try:
            print(f"🧨 Removendo acesso ao módulo: {NETWORK_TOOLS}")
            shutil.move(NETWORK_TOOLS, NETWORK_TOOLS_BACKUP)
            print("✅ Módulo renomeado para .broken")
            # Garante que o backup não seja executável
            os.chmod(NETWORK_TOOLS_BACKUP, stat.S_IREAD)
        except Exception as e:
            print(f"🚨 Falha crítica na simulação: {str(e)}")
            return
    else:
        print("⚠️ Módulo já está quebrado, não encontrado ou sem permissões.")

    print("\n👉 Agora, peça ao Arkanis: 'Minha internet não funciona, o que aconteceu?'")
    print("O Sentinel deve detectar o arquivo .broken e restaurá-lo.")

if __name__ == "__main__":
    simulate()