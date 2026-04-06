import psutil
import time
import os
import platform
from typing import Any, Dict
from tools.base_tool import BaseTool
from tools.registry import registry
from core.logger import logger
import datetime
import json
import socket
from dataclasses import dataclass, asdict

@dataclass
class SystemMetrics:
    """Estrutura de dados padronizada para métricas do sistema"""
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    disk: Dict[str, Any]
    network: Dict[str, Any]
    os: Dict[str, Any]
    status: str
    processes: list = None

_network_stats_cache: Dict[str, Dict] = {'host': None, 'sent': 0, 'recv': 0}


class SystemMonitorTool(BaseTool):
    """
    ARKANIS V3.1 - System Guardian Tool
    Gathers real-time performance metrics (CPU, RAM, Disk, Network).
    Essential for the System Watch dashboard and proactive maintenance.
    """
    
    def __init__(self):
        super().__init__()
        self._timeout = 5.0  # Timeout em segundos para operações de sistema

    @property
    def name(self) -> str:
        return "system_monitor"

    @property
    def description(self) -> str:
        return "Gathers real-time system performance metrics and health status (CPU, RAM, Disk, Network)."

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "detailed": "Optional boolean string ('true' or 'false'). If true, returns process list and network connections.",
            "disk_path": "Optional path to monitor (default: root /). Use '.' for system path."
        }

    def _get_cached_network_delta(self):
        """Calcula o delta de bytes entre chamadas consecutivas"""
        current = psutil.net_io_counters()
        hostname = platform.node()
        
        host = _network_stats_cache.get('host')
        last = _network_stats_cache.get('sent')
        
        # Reinit cache if host changed (system restart or different instance)
        if last is None and host is None:
            _network_stats_cache = {
                'host': hostname,
                'sent': current.bytes_sent,
                'recv': current.bytes_recv
            }
            return {
                'sent_mb': 0.0,
                'recv_mb': 0.0,
                'sent_bytes': current.bytes_sent,
                'recv_bytes': current.bytes_recv
            }
        
        if host is not None and host == hostname and last is not None:
            net_delta = {
                'sent_mb': round((current.bytes_sent - last) / (1024**2), 2),
                'recv_mb': round((current.bytes_recv - _network_stats_cache.get('recv', 0)) / (1024**2), 2),
                'sent_bytes': current.bytes_sent - last,
                'recv_bytes': current.bytes_recv - _network_stats_cache.get('recv', 0)
            }
        else:
            _network_stats_cache['host'] = hostname
            net_delta = {
                'sent_mb': 0.0,
                'recv_mb': 0.0,
                'sent_bytes': current.bytes_sent,
                'recv_bytes': current.bytes_recv
            }
        
        _network_stats_cache['sent'] = current.bytes_sent
        _network_stats_cache['recv'] = current.bytes_recv
        
        return net_delta

    def _get_connections_safe(self, limit: int = 10) -> list:
        """Retorna apenas informações básicas de conexões, ocultando IPs sensíveis"""
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if len(connections) >= limit:
                    break
                try:
                    connections.append({
                        'type': conn.type,
                        'local_port': conn.laddr.port if conn.laddr else None,
                        'remote_port': conn.raddr.port if conn.raddr else None,
                        'status': conn.status,
                        'ip_protected': True  # Flag indicando IPs foram ofuscados
                    })
                except Exception:
                    continue
        except (psutil.AccessDenied, PermissionError) as e:
            logger.warning(f'Access denied to network connections: {e}')
        return connections

    def execute(self, **kwargs) -> Dict[str, Any]:
        detailed = str(kwargs.get('detailed', 'false')).lower() == 'true'
        disk_path = kwargs.get('disk_path', '/')
        if disk_path and disk_path in ('.', 'home'):
            disk_path = os.path.expanduser('~') if disk_path == 'home' else os.path.join(os.sep)
        
        try:
            def get_metrics():
                cpu_percent = psutil.cpu_percent(interval=max(0.1, min(0.5, self._timeout / 10)))
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage(disk_path)
                net = self._get_cached_network_delta()
                
                metrics = {
                    'cpu': {
                        'usage_percent': cpu_percent,
                        'cores': psutil.cpu_count(logical=True),
                        'frequency_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else 0
                    },
                    'memory': {
                        'total_gb': round(memory.total / (1024**3), 2),
                        'available_gb': round(memory.available / (1024**3), 2),
                        'used_percent': memory.percent
                    },
                    'disk': {
                        'path': disk_path,
                        'total_gb': round(disk.total / (1024**3), 2),
                        'free_gb': round(disk.free / (1024**3), 2),
                        'used_percent': disk.percent
                    },
                    'network': {
                        'sent_mb': net['sent_mb'],
                        'recv_mb': net['recv_mb'],
                        'sent_tb': net['sent_bytes'] / (1024**4),
                        'recv_tb': net['recv_bytes'] / (1024**4)
                    },
                    'os': {
                        'system': platform.system(),
                        'release': platform.release(),
                        'machine': platform.machine(),
                        'version': platform.version()
                    },
                    'status': 'online'
                }

                if detailed:
                    procs = []
                    start = time.time()
                    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        if time.time() - start > self._timeout:
                            logger.warning('Process enumeration timeout reached')
                            break
                        try:
                            pid = p.pid
                            info = {'pid': pid}
                            info['name'] = p.info.get('name', 'Unknown')
                            info['cpu_percent'] = float(p.info.get('cpu_percent', 0))
                            info['memory_percent'] = float(p.info.get('memory_percent', 0))
                            procs.append(info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    procs = procs[:5]
                    procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                    metrics['processes'] = procs
                    metrics['network']['connections'] = len(self._get_connections_safe())

                return metrics

            return get_metrics()

        except Exception as e:
            logger.error(f'System Guardian Error: {str(e)}')
            return {'status': 'down', 'error': str(e), 'timestamp': datetime.datetime.now().isoformat()}


class GetCurrentDateTimeTool(BaseTool):
    """A tool to get the current date and time."""
    
    @property
    def name(self) -> str:
        return 'get_current_datetime'

    @property
    def description(self) -> str:
        return 'Returns the current date and time in a formatted string.'

    @property
    def arguments(self) -> Dict[str, str]:
        return {
            'timezone': 'Optional timezone offset in +/-HH:MM format (default: system timezone)'
        }

    def execute(self, **kwargs):
        """Retorna sempre um Dict para consistência com o padrão BaseTool."""
        try:
            now = datetime.datetime.now()
            return {
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'unix_timestamp': int(now.timestamp()),
                'iso_8601': now.isoformat()
            }
        except Exception as e:
            logger.error(f'DateTime Tool Error: {str(e)}')
            return {'error': str(e), 'status': 'error'}

# Alias for compatibility with AutoHealAgent
DiagnosticTool = SystemMonitorTool

_registry_already_initialized = False
if not _registry_already_initialized:
    registry.register(SystemMonitorTool())
    registry.register(GetCurrentDateTimeTool())
    _registry_already_initialized = True