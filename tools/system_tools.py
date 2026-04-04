import psutil
import time
import os
import platform
from typing import Any, Dict
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger

class SystemMonitorTool(BaseTool):
    """
    ARKANIS V3.1 - System Guardian Tool
    Gathers real-time performance metrics (CPU, RAM, Disk, Network).
    Essential for the System Watch dashboard and proactive maintenance.
    """
    
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return "system_monitor"

    @property
    def description(self) -> str:
        return "Gathers real-time system performance metrics and health status (CPU, RAM, Disk, Network)."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "detailed": "Optional boolean string ('true' or 'false'). If true, returns process list and network connections."
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        detailed = str(kwargs.get("detailed", "false")).lower() == "true"
        
        try:
            # Basic Health
            cpu_percent = psutil.cpu_percent(interval=None) # First call usually 0
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()

            metrics = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count(logical=True),
                    "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": disk.percent
                },
                "network": {
                    "sent_mb": round(net.bytes_sent / (1024**2), 2),
                    "recv_mb": round(net.bytes_recv / (1024**2), 2)
                },
                "os": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine()
                },
                "status": "online"
            }

            if detailed:
                # Add top 5 processes by CPU
                procs = []
                for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']), 
                             key=lambda x: x.info['cpu_percent'], reverse=True)[:5]:
                    procs.append(p.info)
                metrics["processes"] = procs
                
                # Active connections count
                metrics["network"]["connections"] = len(psutil.net_connections())

            return metrics

        except Exception as e:
            logger.error(f"System Guardian Error: {str(e)}")
            return {"status": "degraded", "error": str(e)}

# Auto-registration
registry.register(SystemMonitorTool())
