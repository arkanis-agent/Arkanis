import os
import time
import shutil
import stat
import json
import argparse
import sys
import fcntl

# Arkanis Root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NETWORK_TOOLS = os.path.join(ROOT, "tools", "network_tools.py")
NETWORK_TOOLS_BACKUP = NETWORK_TOOLS + ".broken"
SIMULATION_STATE_FILE = os.path.join(ROOT, ".arkanis_sim_state.json")
LOCK_FILE = os.path.join(ROOT, ".simulation.lock")


def save_state(timestamp: float) -> None:
    """Salva o estado da simulação para rastreabilidade"""
    state = {"timestamp": timestamp, "file": NETWORK_TOOLS, "status": "broken"}
    with open(SIMULATION_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def load_state() -> dict | None:
    """Carrega o estado da simulação se existir"""
    if os.path.exists(SIMULATION_STATE_FILE):
        try:
            with open(SIMULATION_STATE_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Erro ao ler estado: {e}")
    return None


def remove_state() -> None:
    """Limpa o arquivo de estado após restauração"""
    if os.path.exists(SIMULATION_STATE_FILE):
        try:
            os.remove(SIMULATION_STATE_FILE)
        except OSError as e:
            print(f"⚠️ Erro ao remover estado: {e}")


def check_safe_to_modify(filepath: str) -> bool:
    """Verifica se podemos modificar o arquivo com segurança"""
    try:
        if not os.path.exists(filepath):
            print(f"⚠️ Arquivo não encontrado: {filepath}")
            return False
        if not os.access(filepath, os.W_OK):
            print(f"⚠️ Sem permissões de escrita em: {filepath}")
            return False
        if check_already_simulated():
            print("⚠️ Simulação já está ativa!")
            return False
        return True
    except Exception as e:
        print(f"🚨 Erro ao verificar arquivo: {str(e)}")
        return False


def check_already_simulated() -> bool:
    """Verifica se já existe simulação ativa"""
    state = load_state()
    return state is not None and state.get('status') == 'broken'


def restore() -> None:
    """Restaura o arquivo network_tools para o estado original"""
    try:
        if load_state() is None:
            print("⚠️ Nenhuma simulação ativa para restaurar.")
            return

        if not os.path.exists(NETWORK_TOOLS_BACKUP):
            print(f"⚠️ Backup não encontrado: {NETWORK_TOOLS_BACKUP}")
            return

        shutil.move(NETWORK_TOOLS_BACKUP, NETWORK_TOOLS)
        os.chmod(NETWORK_TOOLS, 0o644)
        remove_state()
        print("✅ Arquivo restaurado com sucesso!")
    except Exception as e:
        print(f"🚨 Falha na restauração: {str(e)}")


def run_simulate():
    """Executa a simulação de falha catastrófica"""
    print("🔥 [CAOS] Iniciando simulação de falha catastrófica...")

    if check_safe_to_modify(NETWORK_TOOLS):
        try:
            print(f"🧨 Removendo acesso ao módulo: {NETWORK_TOOLS}")
            shutil.move(NETWORK_TOOLS, NETWORK_TOOLS_BACKUP)
            print("✅ Módulo renomeado para .broken")
            save_state(time.time())
            print(f"📋 Estado salvo em: {SIMULATION_STATE_FILE}")
        except Exception as e:
            print(f"🚨 Falha crítica na simulação: {str(e)}")
            return
    else:
        print("⚠️ Módulo já está quebrado, não encontrado ou sem permissões.")
        return

    print("\n👉 AGORA:")
    print("   1. Peça ao Arkanis: 'Minha internet não funciona, o que aconteceu?'")
    print("   2. Para restaurar manualmente: python simulate_failure.py --restore")
    print("   3. Para desligar o modo simulação permanentemente: delete o arquivo .arkanis_sim_state.json")


def main() -> int:
    """Função principal com argparser para CLI"""
    parser = argparse.ArgumentParser(description="Arkanis V3 - Simulador de Falhas de Rede")
    parser.add_argument("--restore", action="store_true", help="Restaura o módulo network_tools")
    parser.add_argument("--release-lock", action="store_true", help="Libera lock de simulação")
    args = parser.parse_args()

    if args.release_lock:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            print("✅ Lock liberado.")
        return 0

    if args.restore:
        restore()
        return 0

    run_simulate()
    return 0


if __name__ == "__main__":
    # Lock para evitar execução simultânea
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
    except (IOError, OSError):
        print("⚠️ Outra instância está rodando a simulação.")
        sys.exit(1)
    finally:
        if lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
