import os
import sys
import platform
import subprocess
import json
import multiprocessing
from enum import Enum
import logging

# Constantes
GB_CONV = 1024 ** 3
MIN_RAM = 8
MIN_DISK = 10
DEFAULT_RAM = 4.0
DEFAULT_DISK = 10.0

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Tier(Enum):
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"

def get_ram_gb():
    """Returns available RAM in GB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        return int(line.split()[1]) / GB_CONV
        elif platform.system() == "Darwin":
            res = subprocess.run(["sysctl", "hw.memsize"], capture_output=True, text=True)
            return int(res.stdout.split(":")[1].strip()) / GB_CONV
    except Exception as e:
        logger.error(f"Erro ao obter RAM: {e}")
    return DEFAULT_RAM

def has_gpu():
    """Detects NVIDIA GPU presence via nvidia-smi."""
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception as e:
        logger.error(f"Erro ao detectar GPU: {e}")
        return False

def get_disk_gb():
    """Returns available disk space in GB."""
    try:
        stat = os.statvfs('/')
        return (stat.f_bavail * stat.f_frsize) / GB_CONV
    except Exception as e:
        logger.error(f"Erro ao obter espaço em disco: {e}")
    return DEFAULT_DISK

def detect_tier(ram_gb, gpu_available):
    """Categorizes system into performance tiers for model selection."""
    if ram_gb < MIN_RAM:
        return Tier.LOW, "llama3.2:3b"
    elif ram_gb < 16:
        return Tier.MID, "llama3.1:8b"
    elif gpu_available:
        return Tier.HIGH, "llama3.1:8b"
    else:
        return Tier.MID, "llama3.1:8b"

def main():
    ram = get_ram_gb()
    gpu = has_gpu()
    cores = multiprocessing.cpu_count()
    disk = get_disk_gb()
    os_name = platform.system()
    arch = platform.machine()
    
    tier, model = detect_tier(ram, gpu)
    
    status = {
        "os": os_name,
        "arch": arch,
        "ram_gb": round(ram, 2),
        "cores": cores,
        "gpu": gpu,
        "disk_gb": round(disk, 2),
        "tier": tier.value,
        "recommended_model": model,
        "capable": ram >= MIN_RAM and disk >= MIN_DISK
    }
    
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()