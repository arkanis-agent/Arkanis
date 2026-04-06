import os
import sys
import platform
import subprocess
import json
import multiprocessing
from enum import Enum
from typing import Tuple, List
import logging

# Constantes
GB_CONV = 1024 ** 3
MIN_RAM = 8
MIN_DISK = 10
DEFAULT_RAM = 4.0
DEFAULT_DISK = 10.0

# Configuração de logging
timeout = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

class Tier(Enum):
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"

def get_ram_gb() -> float:
    """Returns available RAM in GB."""
    try:
        system = platform.system()
        
        if system == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        return int(line.split()[1]) / GB_CONV
        elif system == "Darwin":
            res = subprocess.run(
                ["sysctl", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return int(res.stdout.split(":")[1].strip()) / GB_CONV
        elif system == "Windows":
            res = subprocess.run(
                ["wmic", "OS", "get", "TotalVisibleMemorySize"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "TotalVisibleMemorySize" not in line:
                        try:
                            return int(line) / (1024**2)  # Already in KB
                        except ValueError:
                            pass
    except subprocess.TimeoutExpired:
        logger.error("Timeout ao tentar obter RAM")
    except Exception as e:
        logger.error(f"Erro ao obter RAM: {e}")
    return DEFAULT_RAM

def has_gpu() -> bool:
    """Detects NVIDIA GPU presence via nvidia-smi."""
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return res.returncode == 0 and len(res.stdout.strip()) > 0
    except subprocess.TimeoutExpired:
        logger.warning("Timeout ao verificar GPU")
    except Exception as e:
        logger.warning(f"Falha ao detectar GPU (continua sem GPU): {e}")
        return False

def get_disk_gb() -> float:
    """Returns available disk space in GB for root partition."""
    try:
        stat = os.statvfs('/')
        return (stat.f_bavail * stat.f_frsize) / GB_CONV
    except Exception as e:
        logger.error(f"Erro ao obter espaço em disco: {e}")
    return DEFAULT_DISK

def detect_tier(ram_gb: float, gpu_available: bool) -> Tuple[Tier, str]:
    """Categorizes system into performance tiers for model selection."""
    # Fixed logic: Check GPU before tier limits
    if ram_gb < MIN_RAM:
        logger.info(f"Sistema LOW: RAM={ram_gb:.2f}GB")
        return Tier.LOW, "llama3.2:3b"
    elif ram_gb < 8:
        logger.info(f"Sistema LOW: RAM={ram_gb:.2f}GB")
        return Tier.LOW, "llama3.2:3b"
    elif gpu_available:
        logger.info(f"Sistema HIGH: GPU disponível, RAM={ram_gb:.2f}GB")
        return Tier.HIGH, "llama-3.1-8b"
    elif ram_gb >= 16:
        logger.info(f"Sistema HIGH: RAM={ram_gb:.2f}GB (suficiente para 8b)")
        return Tier.HIGH, "llama-3.1-8b"
    else:
        logger.info(f"Sistema MID: RAM={ram_gb:.2f}GB")
        return Tier.MID, "llama-3.2-3b"

def main() -> None:
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
        "capable": ram >= MIN_RAM and disk >= MIN_DISK,
        "timestamp": platform.timestamp()
    }
    
    json_output = json.dumps(status, indent=2)
    print(json_output)
    
    if not status["capable"]:
        logger.error(f"Sistema insuficiente para Arkanis V3 - RAM: {status['ram_gb']}GB, Disco: {status['disk_gb']}GB")

if __name__ == "__main__":
    main()
