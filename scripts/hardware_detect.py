import os
import sys
import platform
import subprocess
import json
import multiprocessing

def get_ram_gb():
    """Returns available RAM in GB."""
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        return int(line.split()[1]) / (1024 * 1024)
        elif platform.system() == "Darwin":
            res = subprocess.run(["sysctl", "hw.memsize"], capture_output=True, text=True)
            return int(res.stdout.split(":")[1].strip()) / (1024**3)
    except Exception:
        pass
    return 4.0 # Default fallback

def has_gpu():
    """Detects NVIDIA GPU presence via nvidia-smi."""
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def get_disk_gb():
    """Returns available disk space in GB."""
    try:
        stat = os.statvfs('/')
        return (stat.f_bavail * stat.f_frsize) / (1024**3)
    except Exception:
        return 10.0

def detect_tier(ram_gb, gpu_available):
    """Categorizes system into performance tiers for model selection."""
    if ram_gb < 8:
        return "LOW", "llama3.2:3b"
    elif ram_gb < 16:
        return "MID", "llama3.1:8b"
    elif gpu_available:
        return "HIGH", "llama3.1:8b" # Default to 8B even on HIGH for speed, but can go higher
    else:
        return "MID", "llama3.1:8b"

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
        "tier": tier,
        "recommended_model": model,
        "capable": ram >= 8 and disk >= 10
    }
    
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
